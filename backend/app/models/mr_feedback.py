from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MRFeedbackRecord(Base):
    __tablename__ = "mr_feedback_records"
    __table_args__ = (
        sa.CheckConstraint(
            "action IN ('ignore','reopen')",
            name="ck_mr_feedback_records_action",
        ),
        sa.Index("ix_mr_feedback_records_project_created_at", "project_id", "created_at"),
        sa.Index("ix_mr_feedback_records_rule_created_at", "rule_key", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(sa.Integer, index=True)
    merge_request_iid: Mapped[int] = mapped_column(sa.Integer, index=True)
    review_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True, index=True)
    issue_id: Mapped[str] = mapped_column(sa.String(64), index=True)
    rule_key: Mapped[str | None] = mapped_column(sa.String(128), nullable=True, index=True)
    action: Mapped[str] = mapped_column(sa.String(20), index=True)
    reason: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
    operator_gitlab_id: Mapped[int] = mapped_column(sa.Integer, index=True)
    operator_name: Mapped[str] = mapped_column(sa.String(255), default="", server_default="")
    operator_role: Mapped[str | None] = mapped_column(sa.String(64), nullable=True)
    source_note_id: Mapped[int | None] = mapped_column(sa.Integer, nullable=True, index=True)
    source_note_body: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False),
        server_default=sa.func.now(),
        index=True,
    )

