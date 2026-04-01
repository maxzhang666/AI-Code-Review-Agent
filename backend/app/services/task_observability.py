from __future__ import annotations

from datetime import UTC, datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TaskEvent, WeeklySnapshotSchedulerLog

TASK_EVENTS_RETENTION_DAYS = 30
WEEKLY_SCHEDULER_LOGS_RETENTION_DAYS = 90


def build_task_events_retention_cutoff(
    *,
    retention_days: int = TASK_EVENTS_RETENTION_DAYS,
    now: datetime | None = None,
) -> datetime:
    if retention_days <= 0:
        raise ValueError("retention_days must be > 0")
    base_time = now or datetime.now(UTC).replace(tzinfo=None)
    return base_time - timedelta(days=retention_days)


async def cleanup_expired_task_events(
    session: AsyncSession,
    *,
    retention_days: int = TASK_EVENTS_RETENTION_DAYS,
    now: datetime | None = None,
) -> int:
    cutoff = build_task_events_retention_cutoff(retention_days=retention_days, now=now)
    result = await session.execute(
        sa.delete(TaskEvent).where(TaskEvent.created_at < cutoff)
    )
    await session.commit()
    return int(result.rowcount or 0)


def build_weekly_scheduler_logs_retention_cutoff(
    *,
    retention_days: int = WEEKLY_SCHEDULER_LOGS_RETENTION_DAYS,
    now: datetime | None = None,
) -> datetime:
    if retention_days <= 0:
        raise ValueError("retention_days must be > 0")
    base_time = now or datetime.now(UTC).replace(tzinfo=None)
    return base_time - timedelta(days=retention_days)


async def cleanup_expired_weekly_scheduler_logs(
    session: AsyncSession,
    *,
    retention_days: int = WEEKLY_SCHEDULER_LOGS_RETENTION_DAYS,
    now: datetime | None = None,
) -> int:
    cutoff = build_weekly_scheduler_logs_retention_cutoff(
        retention_days=retention_days,
        now=now,
    )
    result = await session.execute(
        sa.delete(WeeklySnapshotSchedulerLog).where(
            WeeklySnapshotSchedulerLog.created_at < cutoff
        )
    )
    await session.commit()
    return int(result.rowcount or 0)
