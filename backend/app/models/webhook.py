from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WebhookLog(Base):
    __tablename__ = "webhook_logs"
    __table_args__ = (
        sa.CheckConstraint(
            "log_level IN ('INFO','WARNING','ERROR')",
            name="ck_webhook_logs_log_level",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(sa.String(100), index=True)
    project_id: Mapped[int] = mapped_column(sa.Integer, index=True)
    project_name: Mapped[str] = mapped_column(sa.String(255))
    merge_request_iid: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    user_name: Mapped[str] = mapped_column(sa.String(255))
    user_email: Mapped[str] = mapped_column(sa.String(255))
    source_branch: Mapped[str] = mapped_column(sa.String(255))
    target_branch: Mapped[str] = mapped_column(sa.String(255))
    payload: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    request_headers: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    request_body_raw: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
    remote_addr: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    request_id: Mapped[str | None] = mapped_column(sa.String(100), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), index=True
    )
    processed: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false()
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=False), nullable=True
    )
    log_level: Mapped[str] = mapped_column(
        sa.String(10), default="INFO", server_default="INFO", index=True
    )
    skip_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    pipeline_trace: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
