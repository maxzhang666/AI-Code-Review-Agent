from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.models import SystemConfig, WeeklySnapshotSchedulerLog
from app.services.reporting.weekly_snapshot_scheduler import (
    DeveloperWeeklySnapshotScheduler,
    _resolve_target_week_start_to_generate,
)


class _FakeQueueManager:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def enqueue(self, payload):  # noqa: ANN001
        self.calls.append(payload.model_dump())
        return f"task-{len(self.calls)}"


def _build_scheduler_settings() -> SimpleNamespace:
    return SimpleNamespace(
        TIMEZONE="Asia/Shanghai",
    )


def test_resolve_target_week_start_to_generate() -> None:
    tz = ZoneInfo("Asia/Shanghai")
    monday_0030 = datetime(2026, 3, 30, 0, 30, tzinfo=tz)
    assert _resolve_target_week_start_to_generate(
        monday_0030,
        trigger_weekday=0,
        trigger_hour=1,
    ) is None

    monday_0105 = datetime(2026, 3, 30, 1, 5, tzinfo=tz)
    target = _resolve_target_week_start_to_generate(
        monday_0105,
        trigger_weekday=0,
        trigger_hour=1,
    )
    assert target is not None
    assert target.isoformat() == "2026-03-23"


@pytest.mark.asyncio
async def test_scheduler_enqueue_if_due_is_idempotent_by_week_marker(db_session) -> None:
    queue_manager = _FakeQueueManager()
    scheduler = DeveloperWeeklySnapshotScheduler(
        queue_manager,
        settings=_build_scheduler_settings(),
    )
    db_session.add_all(
        [
            SystemConfig(key="reports.developer_weekly.auto_enabled", value="true"),
            SystemConfig(key="reports.developer_weekly.auto_trigger_weekday", value="0"),
            SystemConfig(key="reports.developer_weekly.auto_trigger_hour", value="1"),
            SystemConfig(key="reports.developer_weekly.auto_poll_seconds", value="60"),
            SystemConfig(key="reports.developer_weekly.auto_use_llm", value="false"),
        ]
    )
    await db_session.commit()

    now = datetime(2026, 3, 30, 1, 8, tzinfo=ZoneInfo("Asia/Shanghai"))
    first = await scheduler.enqueue_if_due(now=now)
    assert first["status"] == "queued"
    assert first["week_start"] == "2026-03-23"
    assert isinstance(first.get("run_id"), str) and first["run_id"]
    assert len(queue_manager.calls) == 1
    assert queue_manager.calls[0]["task_type"] == "generate_developer_weekly_snapshot"
    assert queue_manager.calls[0]["data"]["use_llm"] is False
    assert queue_manager.calls[0]["data"]["run_id"] == first["run_id"]
    first_log = (
        await db_session.execute(
            select(WeeklySnapshotSchedulerLog).order_by(WeeklySnapshotSchedulerLog.id.desc()).limit(1)
        )
    ).scalars().first()
    assert first_log is not None
    assert first_log.status == "queued"
    assert first_log.run_id == first["run_id"]
    assert first_log.task_id == first["task_id"]

    marker = (
        await db_session.execute(
            select(SystemConfig).where(
                SystemConfig.key == "reports.developer_weekly.auto_last_enqueued_week_start"
            )
        )
    ).scalars().first()
    assert marker is not None
    assert marker.value == "2026-03-23"

    second = await scheduler.enqueue_if_due(now=now)
    assert second["status"] == "skipped"
    assert second["reason"] == "already_enqueued"
    assert len(queue_manager.calls) == 1
    second_log = (
        await db_session.execute(
            select(WeeklySnapshotSchedulerLog).order_by(WeeklySnapshotSchedulerLog.id.desc()).limit(1)
        )
    ).scalars().first()
    assert second_log is not None
    assert second_log.status == "skipped"
    assert second_log.reason == "already_enqueued"


@pytest.mark.asyncio
async def test_scheduler_enqueue_if_due_skips_when_disabled(db_session) -> None:  # noqa: ARG001
    queue_manager = _FakeQueueManager()
    scheduler = DeveloperWeeklySnapshotScheduler(
        queue_manager,
        settings=_build_scheduler_settings(),
    )
    now = datetime(2026, 3, 30, 1, 8, tzinfo=ZoneInfo("Asia/Shanghai"))
    result = await scheduler.enqueue_if_due(now=now)
    assert result["status"] == "skipped"
    assert result["reason"] == "disabled"
    assert queue_manager.calls == []
    latest_log = (
        await db_session.execute(
            select(WeeklySnapshotSchedulerLog).order_by(WeeklySnapshotSchedulerLog.id.desc()).limit(1)
        )
    ).scalars().first()
    assert latest_log is not None
    assert latest_log.status == "skipped"
    assert latest_log.reason == "disabled"


@pytest.mark.asyncio
async def test_scheduler_enqueue_if_due_can_enqueue_ignore_strategy_task(db_session) -> None:
    queue_manager = _FakeQueueManager()
    scheduler = DeveloperWeeklySnapshotScheduler(
        queue_manager,
        settings=_build_scheduler_settings(),
    )
    db_session.add_all(
        [
            SystemConfig(key="reports.developer_weekly.auto_enabled", value="true"),
            SystemConfig(key="reports.developer_weekly.auto_trigger_weekday", value="0"),
            SystemConfig(key="reports.developer_weekly.auto_trigger_hour", value="1"),
            SystemConfig(key="reports.ignore_strategy.auto_enabled", value="true"),
            SystemConfig(key="reports.ignore_strategy.auto_apply", value="false"),
        ]
    )
    await db_session.commit()

    now = datetime(2026, 3, 30, 1, 10, tzinfo=ZoneInfo("Asia/Shanghai"))
    result = await scheduler.enqueue_if_due(now=now)

    assert result["status"] == "queued"
    assert result.get("ignore_strategy_task_id") == "task-2"
    assert isinstance(result.get("run_id"), str) and result["run_id"]
    assert len(queue_manager.calls) == 2
    assert queue_manager.calls[0]["task_type"] == "generate_developer_weekly_snapshot"
    assert queue_manager.calls[1]["task_type"] == "generate_ignore_strategy_weekly"
    assert queue_manager.calls[0]["data"]["run_id"] == result["run_id"]
    assert queue_manager.calls[1]["data"]["run_id"] == result["run_id"]
    assert queue_manager.calls[1]["data"]["apply_changes"] is False
