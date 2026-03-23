from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MergeRequestReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    project_name: str
    merge_request_iid: int
    merge_request_title: str
    source_branch: str
    target_branch: str
    author_name: str
    author_email: str
    review_content: str = ""
    review_score: int | None = None
    files_reviewed: list[str] = Field(default_factory=list)
    total_files: int = 0
    status: str = "pending"
    created_at: datetime | None = None
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    response_sent: bool = False
    response_type: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    is_mock: bool = False
    notification_sent: bool = False
    notification_result: dict[str, Any] = Field(default_factory=dict)
    review_issues: list[dict[str, Any]] = Field(default_factory=list)
    review_summary: str = ""
    review_highlights: list[str] = Field(default_factory=list)
    request_id: str | None = None
