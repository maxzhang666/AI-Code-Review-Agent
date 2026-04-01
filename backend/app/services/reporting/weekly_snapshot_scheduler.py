from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.config import get_settings
from app.core.logging import get_logger
from app.database import get_session_factory
from app.models import SystemConfig, WeeklySnapshotSchedulerLog
from app.queue.types import TaskPayload, TaskPriority

_AUTO_LAST_ENQUEUED_WEEK_START_KEY = "reports.developer_weekly.auto_last_enqueued_week_start"

_AUTO_ENABLED_KEY = "reports.developer_weekly.auto_enabled"
_AUTO_TRIGGER_WEEKDAY_KEY = "reports.developer_weekly.auto_trigger_weekday"
_AUTO_TRIGGER_HOUR_KEY = "reports.developer_weekly.auto_trigger_hour"
_AUTO_POLL_SECONDS_KEY = "reports.developer_weekly.auto_poll_seconds"
_AUTO_USE_LLM_KEY = "reports.developer_weekly.auto_use_llm"
_AUTO_IGNORE_STRATEGY_ENABLED_KEY = "reports.ignore_strategy.auto_enabled"
_AUTO_IGNORE_STRATEGY_APPLY_KEY = "reports.ignore_strategy.auto_apply"

_DEFAULT_AUTO_ENABLED = False
_DEFAULT_TRIGGER_WEEKDAY = 0
_DEFAULT_TRIGGER_HOUR = 1
_DEFAULT_POLL_SECONDS = 300
_DEFAULT_USE_LLM = True
_DEFAULT_IGNORE_STRATEGY_ENABLED = False
_DEFAULT_IGNORE_STRATEGY_APPLY = True


def _resolve_target_week_start_to_generate(
    now_local: datetime,
    *,
    trigger_weekday: int,
    trigger_hour: int,
) -> datetime.date | None:
    if now_local.weekday() != trigger_weekday:
        return None
    if now_local.hour < trigger_hour:
        return None
    current_week_start = now_local.date() - timedelta(days=now_local.weekday())
    return current_week_start - timedelta(days=7)


def _parse_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_int(value: Any, *, default: int, min_value: int, max_value: int) -> int:
    try:
        parsed = int(str(value or "").strip())
    except ValueError:
        parsed = default
    if parsed < min_value or parsed > max_value:
        return default
    return parsed


def _parse_optional_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


class DeveloperWeeklySnapshotScheduler:
    def __init__(self, queue_manager: Any, *, settings: Any | None = None) -> None:
        raw = settings or get_settings()
        self._timezone = str(raw.TIMEZONE)
        self._queue_manager = queue_manager
        self._logger = get_logger(__name__)
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="developer-weekly-snapshot-scheduler")
        self._logger.info("developer_weekly_snapshot_scheduler_started")

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._logger.info("developer_weekly_snapshot_scheduler_stopped")

    async def _load_runtime_config(self, db) -> dict[str, Any]:  # noqa: ANN001
        rows = (
            await db.execute(
                select(SystemConfig.key, SystemConfig.value).where(
                    SystemConfig.key.in_(
                        [
                            _AUTO_ENABLED_KEY,
                            _AUTO_TRIGGER_WEEKDAY_KEY,
                            _AUTO_TRIGGER_HOUR_KEY,
                            _AUTO_POLL_SECONDS_KEY,
                            _AUTO_USE_LLM_KEY,
                            _AUTO_IGNORE_STRATEGY_ENABLED_KEY,
                            _AUTO_IGNORE_STRATEGY_APPLY_KEY,
                        ]
                    )
                )
            )
        ).all()
        raw_map = {str(key): value for key, value in rows}
        return {
            "enabled": _parse_bool(raw_map.get(_AUTO_ENABLED_KEY), default=_DEFAULT_AUTO_ENABLED),
            "trigger_weekday": _parse_int(
                raw_map.get(_AUTO_TRIGGER_WEEKDAY_KEY),
                default=_DEFAULT_TRIGGER_WEEKDAY,
                min_value=0,
                max_value=6,
            ),
            "trigger_hour": _parse_int(
                raw_map.get(_AUTO_TRIGGER_HOUR_KEY),
                default=_DEFAULT_TRIGGER_HOUR,
                min_value=0,
                max_value=23,
            ),
            "poll_seconds": _parse_int(
                raw_map.get(_AUTO_POLL_SECONDS_KEY),
                default=_DEFAULT_POLL_SECONDS,
                min_value=5,
                max_value=3600,
            ),
            "use_llm": _parse_bool(raw_map.get(_AUTO_USE_LLM_KEY), default=_DEFAULT_USE_LLM),
            "ignore_strategy_enabled": _parse_bool(
                raw_map.get(_AUTO_IGNORE_STRATEGY_ENABLED_KEY),
                default=_DEFAULT_IGNORE_STRATEGY_ENABLED,
            ),
            "ignore_strategy_apply": _parse_bool(
                raw_map.get(_AUTO_IGNORE_STRATEGY_APPLY_KEY),
                default=_DEFAULT_IGNORE_STRATEGY_APPLY,
            ),
        }

    async def _record_scheduler_log(self, db, *, runtime: dict[str, Any], result: dict[str, Any]) -> None:  # noqa: ANN001
        try:
            status = str(result.get("status") or "").strip() or "error"
            reason = str(result.get("reason") or "").strip() or None
            details = dict(result)
            poll_seconds: int | None = None
            poll_seconds_raw = result.get("poll_seconds")
            if poll_seconds_raw is not None and str(poll_seconds_raw).strip():
                try:
                    poll_seconds = int(str(poll_seconds_raw).strip())
                except ValueError:
                    poll_seconds = None
            db.add(
                WeeklySnapshotSchedulerLog(
                    status=status,
                    reason=reason,
                    run_id=str(result.get("run_id") or "").strip() or None,
                    task_id=str(result.get("task_id") or "").strip() or None,
                    ignore_strategy_task_id=str(result.get("ignore_strategy_task_id") or "").strip() or None,
                    week_start=_parse_optional_date(result.get("week_start")),
                    reference_date=_parse_optional_date(result.get("reference_date")),
                    poll_seconds=poll_seconds,
                    trigger_weekday=int(runtime.get("trigger_weekday")) if runtime.get("trigger_weekday") is not None else None,
                    trigger_hour=int(runtime.get("trigger_hour")) if runtime.get("trigger_hour") is not None else None,
                    use_llm=bool(runtime.get("use_llm")) if runtime.get("use_llm") is not None else None,
                    ignore_strategy_enabled=(
                        bool(runtime.get("ignore_strategy_enabled"))
                        if runtime.get("ignore_strategy_enabled") is not None
                        else None
                    ),
                    ignore_strategy_apply=(
                        bool(runtime.get("ignore_strategy_apply"))
                        if runtime.get("ignore_strategy_apply") is not None
                        else None
                    ),
                    details=details,
                )
            )
            await db.flush()
        except Exception as exc:
            self._logger.log_error_with_context(
                "developer_weekly_snapshot_scheduler_log_persist_failed",
                error=exc,
                status=result.get("status"),
                reason=result.get("reason"),
            )

    async def _loop(self) -> None:
        while self._running:
            sleep_seconds = _DEFAULT_POLL_SECONDS
            try:
                result = await self.enqueue_if_due()
                sleep_seconds = int(result.get("poll_seconds") or _DEFAULT_POLL_SECONDS)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._logger.log_error_with_context("developer_weekly_snapshot_scheduler_tick_failed", error=exc)
            await asyncio.sleep(max(1, sleep_seconds))

    async def enqueue_if_due(self, *, now: datetime | None = None) -> dict[str, Any]:
        tz = ZoneInfo(self._timezone)
        now_local = now.astimezone(tz) if isinstance(now, datetime) else datetime.now(tz)

        session_factory = get_session_factory()
        async with session_factory() as db:
            runtime = await self._load_runtime_config(db)
            poll_seconds = int(runtime["poll_seconds"])

            if not bool(runtime["enabled"]):
                result = {"status": "skipped", "reason": "disabled", "poll_seconds": poll_seconds}
                await self._record_scheduler_log(db, runtime=runtime, result=result)
                await db.commit()
                return result

            target_week_start = _resolve_target_week_start_to_generate(
                now_local,
                trigger_weekday=int(runtime["trigger_weekday"]),
                trigger_hour=int(runtime["trigger_hour"]),
            )
            if target_week_start is None:
                result = {"status": "skipped", "reason": "not_trigger_time", "poll_seconds": poll_seconds}
                await self._record_scheduler_log(db, runtime=runtime, result=result)
                await db.commit()
                return result

            target_week_start_text = target_week_start.isoformat()
            current_marker = (
                await db.execute(
                    select(SystemConfig).where(SystemConfig.key == _AUTO_LAST_ENQUEUED_WEEK_START_KEY).limit(1)
                )
            ).scalars().first()
            if current_marker is not None and str(current_marker.value or "").strip() == target_week_start_text:
                result = {
                    "status": "skipped",
                    "reason": "already_enqueued",
                    "week_start": target_week_start_text,
                    "poll_seconds": poll_seconds,
                }
                await self._record_scheduler_log(db, runtime=runtime, result=result)
                await db.commit()
                return result

            run_id = str(uuid4())
            task_id = await self._queue_manager.enqueue(
                TaskPayload(
                    task_type="generate_developer_weekly_snapshot",
                    data={
                        "run_id": run_id,
                        "reference_date": now_local.date().isoformat(),
                        "use_llm": bool(runtime["use_llm"]),
                    },
                    priority=TaskPriority.low,
                    max_retries=1,
                )
            )
            queued_ignore_task_id: str | None = None
            if bool(runtime["ignore_strategy_enabled"]):
                queued_ignore_task_id = await self._queue_manager.enqueue(
                    TaskPayload(
                        task_type="generate_ignore_strategy_weekly",
                        data={
                            "run_id": run_id,
                            "reference_date": now_local.date().isoformat(),
                            "apply_changes": bool(runtime["ignore_strategy_apply"]),
                        },
                        priority=TaskPriority.low,
                        max_retries=1,
                    )
                )

            if current_marker is None:
                current_marker = SystemConfig(
                    key=_AUTO_LAST_ENQUEUED_WEEK_START_KEY,
                    value=target_week_start_text,
                    description="Auto scheduler marker for developer weekly snapshot",
                )
                db.add(current_marker)
            else:
                current_marker.value = target_week_start_text

            self._logger.info(
                "developer_weekly_snapshot_auto_enqueued",
                task_id=task_id,
                ignore_task_id=queued_ignore_task_id,
                run_id=run_id,
                week_start=target_week_start_text,
            )
            response = {
                "status": "queued",
                "task_id": task_id,
                "run_id": run_id,
                "week_start": target_week_start_text,
                "reference_date": now_local.date().isoformat(),
                "poll_seconds": poll_seconds,
            }
            if queued_ignore_task_id is not None:
                response["ignore_strategy_task_id"] = queued_ignore_task_id
            await self._record_scheduler_log(db, runtime=runtime, result=response)
            await db.commit()
            return response
