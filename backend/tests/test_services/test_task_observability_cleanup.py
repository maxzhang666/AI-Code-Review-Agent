from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.models import TaskEvent, WeeklySnapshotSchedulerLog
from app.services.task_observability import (
    cleanup_expired_task_events,
    cleanup_expired_weekly_scheduler_logs,
)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_cleanup_expired_task_events_respects_30_day_window(db_session) -> None:
    now = _now()
    old_task_id = str(uuid4())
    new_task_id = str(uuid4())

    db_session.add_all([
        TaskEvent(
            task_id=old_task_id,
            event_type="enqueued",
            status_after="pending",
            attempt_no=0,
            created_at=now - timedelta(days=31),
        ),
        TaskEvent(
            task_id=new_task_id,
            event_type="enqueued",
            status_after="pending",
            attempt_no=0,
            created_at=now - timedelta(days=5),
        ),
    ])
    await db_session.commit()

    deleted = await cleanup_expired_task_events(db_session, now=now)
    assert deleted == 1

    remaining = int(
        (
            await db_session.execute(select(func.count(TaskEvent.id)))
        ).scalar_one()
        or 0
    )
    assert remaining == 1

    remaining_task_ids = {
        row[0]
        for row in (
            await db_session.execute(select(TaskEvent.task_id))
        ).all()
    }
    assert new_task_id in remaining_task_ids
    assert old_task_id not in remaining_task_ids


@pytest.mark.asyncio
async def test_cleanup_expired_weekly_scheduler_logs_respects_90_day_window(db_session) -> None:
    now = _now()

    db_session.add_all([
        WeeklySnapshotSchedulerLog(
            status="skipped",
            reason="disabled",
            created_at=now - timedelta(days=100),
        ),
        WeeklySnapshotSchedulerLog(
            status="queued",
            run_id="run-retain-001",
            task_id=str(uuid4()),
            created_at=now - timedelta(days=10),
        ),
    ])
    await db_session.commit()

    deleted = await cleanup_expired_weekly_scheduler_logs(db_session, now=now)
    assert deleted == 1

    remaining = int(
        (
            await db_session.execute(select(func.count(WeeklySnapshotSchedulerLog.id)))
        ).scalar_one()
        or 0
    )
    assert remaining == 1

    remaining_runs = {
        row[0]
        for row in (
            await db_session.execute(select(WeeklySnapshotSchedulerLog.run_id))
        ).all()
    }
    assert "run-retain-001" in remaining_runs
