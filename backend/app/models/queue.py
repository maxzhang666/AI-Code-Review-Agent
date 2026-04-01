from __future__ import annotations

from datetime import date, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

TASK_STATUSES = ("pending", "processing", "completed", "failed", "retrying")
TASK_EVENT_TYPES = ("enqueued", "started", "retry_scheduled", "completed", "failed")
WEEKLY_SCHEDULER_LOG_STATUSES = ("queued", "skipped", "error")


class TaskRecord(Base):
    __tablename__ = "task_records"
    __table_args__ = (
        sa.CheckConstraint(
            f"status IN {TASK_STATUSES}",
            name="ck_task_records_status",
        ),
        sa.Index("ix_task_records_dequeue", "status", "priority", "created_at"),
    )

    id: Mapped[str] = mapped_column(sa.String(36), primary_key=True)
    task_type: Mapped[str] = mapped_column(sa.String(100), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    status: Mapped[str] = mapped_column(
        sa.String(20), default="pending", server_default="pending", index=True
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(sa.JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default="0")
    max_retries: Mapped[int] = mapped_column(sa.Integer, default=3, server_default="3")
    priority: Mapped[int] = mapped_column(sa.Integer, default=1, server_default="1", index=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), onupdate=sa.func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=False), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=False), nullable=True
    )


class TaskObservation(Base):
    __tablename__ = "task_observations"
    __table_args__ = (
        sa.CheckConstraint(
            f"status IN {TASK_STATUSES}",
            name="ck_task_observations_status",
        ),
    )

    task_id: Mapped[str] = mapped_column(sa.String(36), primary_key=True)
    run_id: Mapped[str | None] = mapped_column(sa.String(64), nullable=True, index=True)
    task_type: Mapped[str] = mapped_column(sa.String(100), index=True)
    status: Mapped[str] = mapped_column(
        sa.String(20), default="pending", server_default="pending", index=True
    )
    priority: Mapped[int] = mapped_column(sa.Integer, default=1, server_default="1")
    retry_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default="0")
    max_retries: Mapped[int] = mapped_column(sa.Integer, default=3, server_default="3")
    payload: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    result: Mapped[dict[str, Any] | None] = mapped_column(sa.JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=False), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=False), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), onupdate=sa.func.now()
    )


class TaskEvent(Base):
    __tablename__ = "task_events"
    __table_args__ = (
        sa.CheckConstraint(
            f"event_type IN {TASK_EVENT_TYPES}",
            name="ck_task_events_event_type",
        ),
        sa.CheckConstraint(
            f"status_after IN {TASK_STATUSES}",
            name="ck_task_events_status_after",
        ),
        sa.CheckConstraint(
            "attempt_no >= 0",
            name="ck_task_events_attempt_no",
        ),
        sa.Index("ix_task_events_task_created", "task_id", "created_at"),
        sa.Index("ix_task_events_run_created", "run_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(sa.String(36), index=True)
    run_id: Mapped[str | None] = mapped_column(sa.String(64), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(sa.String(32))
    status_after: Mapped[str] = mapped_column(sa.String(20))
    attempt_no: Mapped[int] = mapped_column(sa.Integer, default=0, server_default="0")
    message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    event_payload: Mapped[dict[str, Any] | None] = mapped_column(sa.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), index=True
    )


class WeeklySnapshotSchedulerLog(Base):
    __tablename__ = "weekly_snapshot_scheduler_logs"
    __table_args__ = (
        sa.CheckConstraint(
            f"status IN {WEEKLY_SCHEDULER_LOG_STATUSES}",
            name="ck_weekly_snapshot_scheduler_logs_status",
        ),
        sa.Index("ix_weekly_snapshot_scheduler_logs_created", "created_at"),
        sa.Index("ix_weekly_snapshot_scheduler_logs_run", "run_id"),
    )

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(sa.String(16), index=True)
    reason: Mapped[str | None] = mapped_column(sa.String(64), nullable=True, index=True)
    run_id: Mapped[str | None] = mapped_column(sa.String(64), nullable=True, index=True)
    task_id: Mapped[str | None] = mapped_column(sa.String(36), nullable=True, index=True)
    ignore_strategy_task_id: Mapped[str | None] = mapped_column(sa.String(36), nullable=True)
    week_start: Mapped[date | None] = mapped_column(sa.Date, nullable=True, index=True)
    reference_date: Mapped[date | None] = mapped_column(sa.Date, nullable=True)
    poll_seconds: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    trigger_weekday: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    trigger_hour: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    use_llm: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    ignore_strategy_enabled: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    ignore_strategy_apply: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    details: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), index=True
    )
