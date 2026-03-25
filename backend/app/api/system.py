from __future__ import annotations

import os
import platform
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
    TaskRecord,
    WebhookEventRule,
    WebhookLog,
)
from app.queue.types import TaskPayload, TaskPriority
from app.schemas.system_config import SystemConfigItem, SystemConfigUpdate

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
    payload = TaskPayload(
        task_type="generate_developer_weekly_snapshot",
        data={
            "reference_date": body.get("reference_date"),
            "include_statuses": include_statuses,
            "use_llm": bool(body.get("use_llm", True)),
        },
        priority=TaskPriority.low,
        max_retries=1,
    )
    task_id = await queue_manager.enqueue(payload)
    logger = get_logger(__name__, request_id)
    logger.info("developer_weekly_snapshot_enqueued", task_id=task_id)
    return {"code": 202, "message": "Weekly developer summary generation queued", "task_id": task_id}


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
