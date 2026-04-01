from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProjectIgnoreStrategy(Base):
    __tablename__ = "project_ignore_strategies"
    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('active','expired','disabled')",
            name="ck_project_ignore_strategies_status",
        ),
        sa.Index(
            "ix_project_ignore_strategies_project_status_expire_at",
            "project_id",
            "status",
            "expire_at",
        ),
        sa.Index(
            "ix_project_ignore_strategies_project_signature",
            "project_id",
            "signature",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(sa.Integer, index=True)
    rule_key: Mapped[str] = mapped_column(sa.String(128), default="", server_default="", index=True)
    path_pattern: Mapped[str | None] = mapped_column(sa.String(255), nullable=True, index=True)
    signature: Mapped[str] = mapped_column(sa.String(255), default="", server_default="", index=True)
    title: Mapped[str] = mapped_column(sa.String(255), default="", server_default="")
    reason_summary: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
    ignore_condition: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
    boundary_condition: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
    sample_count_4w: Mapped[int] = mapped_column(sa.Integer, default=0, server_default="0")
    active_weeks_4w: Mapped[int] = mapped_column(sa.Integer, default=0, server_default="0")
    confidence_score: Mapped[float] = mapped_column(sa.Float, default=0.0, server_default="0")
    status: Mapped[str] = mapped_column(sa.String(20), default="active", server_default="active", index=True)
    effective_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=False), nullable=True)
    expire_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=False), nullable=True, index=True)
    disabled_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=False), nullable=True)
    disabled_reason: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), onupdate=sa.func.now()
    )
