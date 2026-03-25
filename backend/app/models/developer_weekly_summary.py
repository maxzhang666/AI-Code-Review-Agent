from __future__ import annotations

from datetime import date, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DeveloperWeeklySummary(Base):
    __tablename__ = "developer_weekly_summaries"
    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('completed','failed')",
            name="ck_developer_weekly_summaries_status",
        ),
        sa.CheckConstraint(
            "source IN ('llm','heuristic')",
            name="ck_developer_weekly_summaries_source",
        ),
        sa.UniqueConstraint(
            "week_start",
            "owner_name",
            "include_statuses_key",
            name="uq_developer_weekly_summaries_scope",
        ),
        sa.Index(
            "ix_developer_weekly_summaries_week_status",
            "week_start",
            "status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    week_start: Mapped[date] = mapped_column(sa.Date, index=True)
    week_end: Mapped[date] = mapped_column(sa.Date)
    owner_name: Mapped[str] = mapped_column(sa.String(255), index=True)
    owner_email: Mapped[str | None] = mapped_column(sa.String(255), nullable=True, index=True)
    include_statuses_key: Mapped[str] = mapped_column(sa.String(100), default="", server_default="", index=True)
    include_statuses: Mapped[list[str]] = mapped_column(sa.JSON, default=list)
    status: Mapped[str] = mapped_column(sa.String(20), default="completed", server_default="completed", index=True)
    source: Mapped[str] = mapped_column(sa.String(20), default="heuristic", server_default="heuristic")
    llm_provider: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    ai_summary: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
    report_payload: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    card_payload: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    generated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False),
        server_default=sa.func.now(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False),
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )
