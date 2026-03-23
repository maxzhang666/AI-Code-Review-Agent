from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MergeRequestReview(Base):
    __tablename__ = "merge_request_reviews"
    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('pending','processing','completed','failed')",
            name="ck_merge_request_reviews_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(sa.Integer, index=True)
    project_name: Mapped[str] = mapped_column(sa.String(255))
    merge_request_iid: Mapped[int] = mapped_column(sa.Integer, index=True)
    merge_request_title: Mapped[str] = mapped_column(sa.String(500))
    source_branch: Mapped[str] = mapped_column(sa.String(255))
    target_branch: Mapped[str] = mapped_column(sa.String(255))
    author_name: Mapped[str] = mapped_column(sa.String(255))
    author_email: Mapped[str] = mapped_column(sa.String(255))
    review_content: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
    review_score: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    files_reviewed: Mapped[list[str]] = mapped_column(sa.JSON, default=list)
    total_files: Mapped[int] = mapped_column(sa.Integer, default=0, server_default="0")
    status: Mapped[str] = mapped_column(
        sa.String(20), default="pending", server_default="pending", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), onupdate=sa.func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=False), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    response_sent: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false()
    )
    response_type: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(sa.String(100), nullable=True)
    is_mock: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false()
    )
    notification_sent: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false()
    )
    notification_result: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    review_issues: Mapped[list[dict[str, Any]]] = mapped_column(sa.JSON, default=list)
    review_summary: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
    review_highlights: Mapped[list[str]] = mapped_column(sa.JSON, default=list)
    request_id: Mapped[str | None] = mapped_column(sa.String(100), nullable=True, index=True)
