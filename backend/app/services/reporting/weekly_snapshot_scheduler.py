from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.config import get_settings
from app.core.logging import get_logger
from app.database import get_session_factory
from app.models import SystemConfig
from app.queue.types import TaskPayload, TaskPriority

_AUTO_LAST_ENQUEUED_WEEK_START_KEY = "reports.developer_weekly.auto_last_enqueued_week_start"

_AUTO_ENABLED_KEY = "reports.developer_weekly.auto_enabled"
_AUTO_TRIGGER_WEEKDAY_KEY = "reports.developer_weekly.auto_trigger_weekday"
_AUTO_TRIGGER_HOUR_KEY = "reports.developer_weekly.auto_trigger_hour"
_AUTO_POLL_SECONDS_KEY = "reports.developer_weekly.auto_poll_seconds"
_AUTO_USE_LLM_KEY = "reports.developer_weekly.auto_use_llm"

_DEFAULT_AUTO_ENABLED = False
_DEFAULT_TRIGGER_WEEKDAY = 0
_DEFAULT_TRIGGER_HOUR = 1
_DEFAULT_POLL_SECONDS = 300
_DEFAULT_USE_LLM = True


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
        }

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
                return {"status": "skipped", "reason": "disabled", "poll_seconds": poll_seconds}

            target_week_start = _resolve_target_week_start_to_generate(
                now_local,
                trigger_weekday=int(runtime["trigger_weekday"]),
                trigger_hour=int(runtime["trigger_hour"]),
            )
            if target_week_start is None:
                return {"status": "skipped", "reason": "not_trigger_time", "poll_seconds": poll_seconds}

            target_week_start_text = target_week_start.isoformat()
            current_marker = (
                await db.execute(
                    select(SystemConfig).where(SystemConfig.key == _AUTO_LAST_ENQUEUED_WEEK_START_KEY).limit(1)
                )
            ).scalars().first()
            if current_marker is not None and str(current_marker.value or "").strip() == target_week_start_text:
                return {
                    "status": "skipped",
                    "reason": "already_enqueued",
                    "week_start": target_week_start_text,
                    "poll_seconds": poll_seconds,
                }

            task_id = await self._queue_manager.enqueue(
                TaskPayload(
                    task_type="generate_developer_weekly_snapshot",
                    data={
                        "reference_date": now_local.date().isoformat(),
                        "use_llm": bool(runtime["use_llm"]),
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
            await db.commit()

            self._logger.info(
                "developer_weekly_snapshot_auto_enqueued",
                task_id=task_id,
                week_start=target_week_start_text,
            )
            return {
                "status": "queued",
                "task_id": task_id,
                "week_start": target_week_start_text,
                "reference_date": now_local.date().isoformat(),
                "poll_seconds": poll_seconds,
            }
