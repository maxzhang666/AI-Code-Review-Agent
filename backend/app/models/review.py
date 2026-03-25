from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    findings: Mapped[list["ReviewFinding"]] = relationship(
        "ReviewFinding", back_populates="review", cascade="all, delete-orphan"
    )


class ReviewFinding(Base):
    __tablename__ = "review_findings"
    __table_args__ = (
        sa.CheckConstraint(
            "severity IN ('critical','high','medium','low')",
            name="ck_review_findings_severity",
        ),
        sa.Index("ix_review_findings_category_severity_created_at", "category", "severity", "created_at"),
        sa.Index("ix_review_findings_owner_name_created_at", "owner_name", "created_at"),
        sa.Index("ix_review_findings_owner_email_created_at", "owner_email", "created_at"),
        sa.Index("ix_review_findings_owner_created_at", "owner", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(
        sa.ForeignKey("merge_request_reviews.id", ondelete="CASCADE"),
        index=True,
    )
    issue_id: Mapped[str] = mapped_column(sa.String(64), default="", server_default="", index=True)
    fingerprint: Mapped[str] = mapped_column(sa.String(64), index=True)
    category: Mapped[str] = mapped_column(sa.String(100), default="quality", server_default="quality")
    subcategory: Mapped[str] = mapped_column(sa.String(100), default="", server_default="")
    severity: Mapped[str] = mapped_column(sa.String(20), default="medium", server_default="medium", index=True)
    confidence: Mapped[float | None] = mapped_column(sa.Float, nullable=True)
    file_path: Mapped[str] = mapped_column(sa.String(1000), default="", server_default="")
    line_start: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    line_end: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    message: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
    suggestion: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
    code_snippet: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
    owner_name: Mapped[str | None] = mapped_column(sa.String(255), nullable=True, index=True)
    owner_email: Mapped[str | None] = mapped_column(sa.String(255), nullable=True, index=True)
    owner: Mapped[str | None] = mapped_column(sa.String(255), nullable=True, index=True)
    is_blocking: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false(), index=True
    )
    is_false_positive: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), onupdate=sa.func.now()
    )

    review: Mapped[MergeRequestReview] = relationship("MergeRequestReview", back_populates="findings")
    actions: Mapped[list["ReviewFindingAction"]] = relationship(
        "ReviewFindingAction", back_populates="finding", cascade="all, delete-orphan"
    )


class ReviewFindingAction(Base):
    __tablename__ = "review_finding_actions"
    __table_args__ = (
        sa.CheckConstraint(
            "action_type IN ('fixed','ignored','todo','reopened')",
            name="ck_review_finding_actions_action_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(
        sa.ForeignKey("review_findings.id", ondelete="CASCADE"),
        index=True,
    )
    action_type: Mapped[str] = mapped_column(sa.String(20), index=True)
    actor: Mapped[str] = mapped_column(sa.String(255))
    note: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
    action_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), index=True
    )

    finding: Mapped[ReviewFinding] = relationship("ReviewFinding", back_populates="actions")
