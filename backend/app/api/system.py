from __future__ import annotations

import os
import platform
import sys
import time
from collections import deque
from datetime import UTC, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import psutil
from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.core.deps import get_current_settings, get_db, get_request_id
from app.core.logging import get_logger
from app.models import (
    LLMProvider,
    MergeRequestReview,
    NotificationChannel,
    Project,
    SystemConfig,
    TaskEvent,
    TaskObservation,
    TaskRecord,
    WeeklySnapshotSchedulerLog,
    WebhookEventRule,
    WebhookLog,
)
from app.queue.types import TaskPayload, TaskPriority
from app.services.task_observability import (
    TASK_EVENTS_RETENTION_DAYS,
    WEEKLY_SCHEDULER_LOGS_RETENTION_DAYS,
    build_task_events_retention_cutoff,
    build_weekly_scheduler_logs_retention_cutoff,
    cleanup_expired_task_events,
    cleanup_expired_weekly_scheduler_logs,
)
from app.schemas.system_config import SystemConfigItem, SystemConfigUpdate
from app.schemas.scheduler_observability import (
    WeeklySnapshotSchedulerLogItem,
    WeeklySnapshotSchedulerLogListResponse,
)
from app.schemas.task_observability import (
    TaskDetailResponse,
    TaskEventItem,
    TaskListResponse,
    TaskObservationItem,
    TaskSummaryResponse,
)

router = APIRouter()

_BOOT_TIME = time.time()


def _detect_system_timezone() -> str:
    local_tz = datetime.now().astimezone().tzinfo
    if isinstance(local_tz, ZoneInfo):
        return local_tz.key

    tz_name = datetime.now().astimezone().tzname()
    if tz_name:
        return tz_name

    if local_tz is not None:
        return str(local_tz)

    return "UTC"


def _format_uptime(seconds: float) -> str:
    d = int(seconds // 86400)
    h = int(seconds % 86400 // 3600)
    m = int(seconds % 3600 // 60)
    parts = []
    if d:
        parts.append(f"{d}天")
    if h:
        parts.append(f"{h}小时")
    parts.append(f"{m}分钟")
    return " ".join(parts)


def _detect_database_type(database_url: str | None) -> str:
    if not database_url:
        return "unknown"
    normalized = database_url.lower()
    if normalized.startswith("sqlite"):
        return "sqlite"
    if normalized.startswith("postgresql"):
        return "postgresql"
    return "unknown"


def _resolve_log_dir(log_dir: str) -> Path:
    return Path(log_dir).expanduser().resolve()


def _resolve_log_file_path(log_dir: Path, filename: str) -> Path:
    candidate = (log_dir / filename).resolve()
    try:
        candidate.relative_to(log_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid filename.") from exc
    return candidate


def _duration_ms(started_at: datetime | None, completed_at: datetime | None) -> int | None:
    if started_at is None:
        return None
    end = completed_at or datetime.now(UTC).replace(tzinfo=None)
    delta_ms = int((end - started_at).total_seconds() * 1000)
    return max(delta_ms, 0)


def _to_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _to_task_observation_item(observation: TaskObservation) -> TaskObservationItem:
    return TaskObservationItem(
        task_id=observation.task_id,
        run_id=observation.run_id,
        task_type=observation.task_type,
        status=observation.status,
        priority=observation.priority,
        retry_count=observation.retry_count,
        max_retries=observation.max_retries,
        payload=observation.payload or {},
        result=observation.result,
        error_message=observation.error_message,
        created_at=observation.created_at,
        started_at=observation.started_at,
        completed_at=observation.completed_at,
        updated_at=observation.updated_at,
        duration_ms=_duration_ms(observation.started_at, observation.completed_at),
    )


def _to_weekly_scheduler_log_item(log_row: WeeklySnapshotSchedulerLog) -> WeeklySnapshotSchedulerLogItem:
    return WeeklySnapshotSchedulerLogItem.model_validate(log_row)


def _parse_retention_days(
    body: dict[str, Any],
    *,
    default_days: int,
) -> int:
    raw = body.get("retention_days", default_days)
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="retention_days must be an integer.") from exc
    if value <= 0 or value > 3650:
        raise HTTPException(status_code=400, detail="retention_days must be between 1 and 3650.")
    return value


@router.get("/system/info")
async def get_system_info(
    request_id: str | None = Depends(get_request_id),
) -> dict[str, Any]:
    settings = get_settings()
    logger = get_logger(__name__, request_id)
    logger.info("system_info_requested")

    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.1)
    uptime_secs = time.time() - _BOOT_TIME

    return {
        "status": "ok",
        "projectName": "AI Code Review",
        "projectVersion": "0.0.1",
        "pythonVersion": sys.version.split(" ")[0],
        "serverStatus": "running",
        "uptime": _format_uptime(uptime_secs),
        "cpu": round(cpu, 1),
        "memory": round(mem.percent, 1),
        "memoryUsed": f"{mem.used / (1024 ** 3):.1f} GB",
        "memoryTotal": f"{mem.total / (1024 ** 3):.1f} GB",
        "platform": platform.platform(),
        "timezone": _detect_system_timezone(),
        "databaseType": _detect_database_type(getattr(settings, "DATABASE_URL", None)),
        "debug": settings.DEBUG,
    }


@router.get("/statistics")
async def get_statistics(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    projects_count = len((await db.execute(select(Project.id))).all())
    reviews_count = len((await db.execute(select(MergeRequestReview.id))).all())
    logs_count = len((await db.execute(select(WebhookLog.id))).all())
    channels_count = len((await db.execute(select(NotificationChannel.id))).all())
    rules_count = len((await db.execute(select(WebhookEventRule.id))).all())
    providers_count = len((await db.execute(select(LLMProvider.id))).all())

    tasks_by_status_rows = (
        await db.execute(select(TaskRecord.status, func.count(TaskRecord.id)).group_by(TaskRecord.status))
    ).all()
    tasks_by_status = {status: count for status, count in tasks_by_status_rows}

    return {
        "projects": projects_count,
        "reviews": reviews_count,
        "webhook_logs": logs_count,
        "notification_channels": channels_count,
        "webhook_event_rules": rules_count,
        "llm_providers": providers_count,
        "tasks_by_status": tasks_by_status,
    }


@router.get("/system/log-files/")
async def list_system_log_files(
    settings=Depends(get_current_settings),
) -> dict[str, Any]:
    log_dir = _resolve_log_dir(settings.LOG_DIR)
    if not log_dir.exists() or not log_dir.is_dir():
        return {"count": 0, "results": []}

    files: list[dict[str, Any]] = []
    for file_path in log_dir.iterdir():
        if not file_path.is_file():
            continue
        stat = file_path.stat()
        files.append(
            {
                "name": file_path.name,
                "size_bytes": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
            }
        )
    files.sort(key=lambda item: item["modified_at"], reverse=True)
    return {"count": len(files), "results": files}


@router.get("/system/log-files/content/")
async def get_system_log_file_content(
    filename: str,
    lines: int = 300,
    settings=Depends(get_current_settings),
) -> dict[str, Any]:
    if not filename.strip():
        raise HTTPException(status_code=400, detail="Filename is required.")
    if lines < 1 or lines > 5000:
        raise HTTPException(status_code=400, detail="lines must be between 1 and 5000.")

    log_dir = _resolve_log_dir(settings.LOG_DIR)
    if not log_dir.exists() or not log_dir.is_dir():
        raise HTTPException(status_code=404, detail="Log directory not found.")

    file_path = _resolve_log_file_path(log_dir, filename)
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Log file not found.")

    buffer: deque[str] = deque(maxlen=lines)
    total_lines = 0
    with file_path.open("r", encoding="utf-8", errors="replace") as fp:
        for line in fp:
            total_lines += 1
            buffer.append(line)

    content = "".join(reversed(buffer))
    returned_lines = len(buffer)
    return {
        "file": file_path.name,
        "total_lines": total_lines,
        "returned_lines": returned_lines,
        "truncated": total_lines > returned_lines,
        "content": content,
    }


@router.get("/system/tasks/summary", response_model=TaskSummaryResponse)
async def get_tasks_summary(
    db: AsyncSession = Depends(get_db),
) -> TaskSummaryResponse:
    settings = get_settings()
    queue_backend = settings.TASK_QUEUE_BACKEND.value

    by_status_rows = (
        await db.execute(
            select(TaskObservation.status, func.count(TaskObservation.task_id))
            .group_by(TaskObservation.status)
        )
    ).all()
    by_task_type_rows = (
        await db.execute(
            select(TaskObservation.task_type, func.count(TaskObservation.task_id))
            .group_by(TaskObservation.task_type)
        )
    ).all()

    return TaskSummaryResponse(
        queue_backend=queue_backend,
        is_persistent=queue_backend != "memory",
        observability_persistent=True,
        by_status={status: int(count) for status, count in by_status_rows},
        by_task_type={task_type: int(count) for task_type, count in by_task_type_rows},
    )


@router.get("/system/tasks/", response_model=TaskListResponse)
async def list_tasks_observations(
    page: int = 1,
    limit: int = 20,
    status: str | None = None,
    task_type: str | None = None,
    task_id: str | None = None,
    run_id: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    db: AsyncSession = Depends(get_db),
) -> TaskListResponse:
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be >= 1.")
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 200.")

    conditions = []
    if status:
        conditions.append(TaskObservation.status == status.strip())
    if task_type:
        conditions.append(TaskObservation.task_type == task_type.strip())
    if task_id:
        conditions.append(TaskObservation.task_id == task_id.strip())
    if run_id:
        conditions.append(TaskObservation.run_id == run_id.strip())
    if created_from:
        conditions.append(TaskObservation.created_at >= _to_naive_utc(created_from))
    if created_to:
        conditions.append(TaskObservation.created_at <= _to_naive_utc(created_to))

    count_stmt = select(func.count(TaskObservation.task_id))
    list_stmt = select(TaskObservation).order_by(TaskObservation.created_at.desc())
    if conditions:
        count_stmt = count_stmt.where(*conditions)
        list_stmt = list_stmt.where(*conditions)

    total = int((await db.execute(count_stmt)).scalar_one() or 0)
    rows = (
        await db.execute(
            list_stmt.offset((page - 1) * limit).limit(limit)
        )
    ).scalars().all()

    return TaskListResponse(
        count=total,
        results=[_to_task_observation_item(row) for row in rows],
    )


@router.get("/system/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task_observation_detail(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> TaskDetailResponse:
    task_id_str = str(task_id)
    observation = await db.get(TaskObservation, task_id_str)
    if observation is None:
        raise HTTPException(status_code=404, detail="Task not found.")

    events = (
        await db.execute(
            select(TaskEvent)
            .where(TaskEvent.task_id == task_id_str)
            .order_by(TaskEvent.created_at.desc())
            .limit(50)
        )
    ).scalars().all()

    base = _to_task_observation_item(observation)
    return TaskDetailResponse(
        **base.model_dump(),
        events=[TaskEventItem.model_validate(event) for event in events],
    )


@router.get("/system/tasks/{task_id}/events", response_model=list[TaskEventItem])
async def list_task_observation_events(
    task_id: UUID,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
) -> list[TaskEventItem]:
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 1000.")

    task_id_str = str(task_id)
    task_exists = (
        await db.execute(
            select(TaskObservation.task_id).where(TaskObservation.task_id == task_id_str).limit(1)
        )
    ).scalar_one_or_none()
    if task_exists is None:
        raise HTTPException(status_code=404, detail="Task not found.")

    rows = (
        await db.execute(
            select(TaskEvent)
            .where(TaskEvent.task_id == task_id_str)
            .order_by(TaskEvent.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [TaskEventItem.model_validate(row) for row in rows]


@router.get(
    "/system/reports/developers/weekly/scheduler-logs",
    response_model=WeeklySnapshotSchedulerLogListResponse,
)
async def list_weekly_snapshot_scheduler_logs(
    page: int = 1,
    limit: int = 50,
    status: str | None = None,
    reason: str | None = None,
    run_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> WeeklySnapshotSchedulerLogListResponse:
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be >= 1.")
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500.")

    conditions = []
    if status:
        conditions.append(WeeklySnapshotSchedulerLog.status == status.strip())
    if reason:
        conditions.append(WeeklySnapshotSchedulerLog.reason == reason.strip())
    if run_id:
        conditions.append(WeeklySnapshotSchedulerLog.run_id == run_id.strip())

    stmt = select(WeeklySnapshotSchedulerLog).order_by(
        WeeklySnapshotSchedulerLog.created_at.desc(),
        WeeklySnapshotSchedulerLog.id.desc(),
    )
    count_stmt = select(func.count(WeeklySnapshotSchedulerLog.id))
    if conditions:
        stmt = stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)

    rows = (
        await db.execute(
            stmt.offset((page - 1) * limit).limit(limit)
        )
    ).scalars().all()
    total = int((await db.execute(count_stmt)).scalar_one() or 0)
    return WeeklySnapshotSchedulerLogListResponse(
        count=total,
        results=[_to_weekly_scheduler_log_item(row) for row in rows],
    )


@router.post("/system/maintenance/cleanup/task-events")
async def cleanup_task_events_maintenance(
    body: dict[str, Any] = Body(default_factory=dict),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    retention_days = _parse_retention_days(body, default_days=TASK_EVENTS_RETENTION_DAYS)
    dry_run = bool(body.get("dry_run", True))
    cutoff = build_task_events_retention_cutoff(retention_days=retention_days)
    stale_count = int(
        (
            await db.execute(
                select(func.count(TaskEvent.id)).where(TaskEvent.created_at < cutoff)
            )
        ).scalar_one()
        or 0
    )
    deleted_count = 0
    if not dry_run:
        deleted_count = await cleanup_expired_task_events(
            db,
            retention_days=retention_days,
        )

    return {
        "resource": "task_events",
        "retention_days": retention_days,
        "dry_run": dry_run,
        "cutoff": cutoff.isoformat(timespec="seconds"),
        "stale_count": stale_count,
        "deleted_count": deleted_count,
    }


@router.post("/system/maintenance/cleanup/weekly-scheduler-logs")
async def cleanup_weekly_scheduler_logs_maintenance(
    body: dict[str, Any] = Body(default_factory=dict),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    retention_days = _parse_retention_days(
        body,
        default_days=WEEKLY_SCHEDULER_LOGS_RETENTION_DAYS,
    )
    dry_run = bool(body.get("dry_run", True))
    cutoff = build_weekly_scheduler_logs_retention_cutoff(
        retention_days=retention_days
    )
    stale_count = int(
        (
            await db.execute(
                select(func.count(WeeklySnapshotSchedulerLog.id)).where(
                    WeeklySnapshotSchedulerLog.created_at < cutoff
                )
            )
        ).scalar_one()
        or 0
    )
    deleted_count = 0
    if not dry_run:
        deleted_count = await cleanup_expired_weekly_scheduler_logs(
            db,
            retention_days=retention_days,
        )

    return {
        "resource": "weekly_snapshot_scheduler_logs",
        "retention_days": retention_days,
        "dry_run": dry_run,
        "cutoff": cutoff.isoformat(timespec="seconds"),
        "stale_count": stale_count,
        "deleted_count": deleted_count,
    }


@router.post("/test/webhook")
async def test_webhook(
    request: Request,
    body: dict[str, Any] = Body(default_factory=dict),
    request_id: str | None = Depends(get_request_id),
) -> dict[str, Any]:
    queue_manager = getattr(request.app.state, "queue_manager", None)
    if queue_manager is None:
        raise HTTPException(status_code=503, detail="Queue manager is not available.")

    payload = TaskPayload(
        task_type="review_mr",
        data={
            "payload": body.get("payload", {}),
            "project_id": body.get("project_id"),
            "source": "system_test",
        },
        priority=TaskPriority.normal,
        max_retries=3,
    )
    task_id = await queue_manager.enqueue(payload)
    logger = get_logger(__name__, request_id)
    logger.info("test_webhook_enqueued", task_id=task_id)
    return {"code": 202, "message": "Test webhook queued", "task_id": task_id}


@router.post("/system/reports/developers/weekly/generate-last-week")
async def enqueue_last_week_developer_summary_generation(
    request: Request,
    body: dict[str, Any] = Body(default_factory=dict),
    request_id: str | None = Depends(get_request_id),
) -> dict[str, Any]:
    queue_manager = getattr(request.app.state, "queue_manager", None)
    if queue_manager is None:
        raise HTTPException(status_code=503, detail="Queue manager is not available.")

    include_statuses_raw = body.get("include_statuses")
    include_statuses = (
        [str(item).strip() for item in include_statuses_raw if str(item).strip()]
        if isinstance(include_statuses_raw, list)
        else None
    )
    run_id = str(uuid4())
    payload = TaskPayload(
        task_type="generate_developer_weekly_snapshot",
        data={
            "run_id": run_id,
            "reference_date": body.get("reference_date"),
            "include_statuses": include_statuses,
            "use_llm": bool(body.get("use_llm", True)),
        },
        priority=TaskPriority.low,
        max_retries=1,
    )
    task_id = await queue_manager.enqueue(payload)
    logger = get_logger(__name__, request_id)
    logger.info("developer_weekly_snapshot_enqueued", task_id=task_id, run_id=run_id)
    return {
        "code": 202,
        "message": "Weekly developer summary generation queued",
        "task_id": task_id,
        "run_id": run_id,
    }


async def get_config_value(db: AsyncSession, key: str, default: str = "") -> str:
    row = (
        await db.execute(select(SystemConfig).where(SystemConfig.key == key).limit(1))
    ).scalars().first()
    return row.value if row is not None else default


@router.get("/system/configs/")
async def list_system_configs(
    db: AsyncSession = Depends(get_db),
) -> list[SystemConfigItem]:
    rows = (await db.execute(select(SystemConfig).order_by(SystemConfig.key))).scalars().all()
    return [SystemConfigItem(key=r.key, value=r.value, description=r.description) for r in rows]


@router.put("/system/configs/")
async def update_system_configs(
    payload: SystemConfigUpdate,
    db: AsyncSession = Depends(get_db),
    request_id: str | None = Depends(get_request_id),
) -> dict[str, Any]:
    logger = get_logger(__name__, request_id)
    for key, value in payload.configs.items():
        row = (
            await db.execute(select(SystemConfig).where(SystemConfig.key == key).limit(1))
        ).scalars().first()
        if row is None:
            db.add(SystemConfig(key=key, value=value))
        else:
            row.value = value
    await db.commit()
    logger.info("system_configs_updated", keys=list(payload.configs.keys()))
    return {"code": 200, "message": "System configs updated"}
