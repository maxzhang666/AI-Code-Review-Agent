from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TaskRecord(Base):
    __tablename__ = "task_records"
    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('pending','processing','completed','failed','retrying')",
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
