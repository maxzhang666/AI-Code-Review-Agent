from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

REVIEW_FINDING_BATCH_MAX_IDS = 500
IGNORE_REASON_CODES = (
    "business_exception",
    "historical_debt",
    "rule_false_positive",
    "defer_fix",
    "duplicate",
    "other",
)
IGNORE_REASON_CODE_PATTERN = "^(business_exception|historical_debt|rule_false_positive|defer_fix|duplicate|other)$"


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


class ReviewFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    review_id: int
    fingerprint: str
    category: str
    subcategory: str = ""
    severity: str
    confidence: float | None = None
    file_path: str = ""
    line_start: int | None = None
    line_end: int | None = None
    message: str = ""
    suggestion: str = ""
    code_snippet: str = ""
    owner_name: str | None = None
    owner_email: str | None = None
    owner: str | None = None
    is_blocking: bool = False
    is_false_positive: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ReviewFindingActionCreate(BaseModel):
    action_type: str = Field(pattern="^(fixed|ignored|todo|reopened)$")
    actor: str | None = Field(default=None, max_length=255)
    note: str = ""
    ignore_reason_code: str | None = Field(default=None, pattern=IGNORE_REASON_CODE_PATTERN)
    ignore_reason_note: str = ""


class ReviewFindingActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    finding_id: int
    action_type: str
    actor: str
    note: str = ""
    ignore_reason_code: str = ""
    ignore_reason_note: str = ""
    actor_user_id: int | None = None
    actor_username: str = ""
    source: str = ""
    action_at: datetime | None = None


class ReviewFindingWorkbenchReviewMeta(BaseModel):
    id: int
    project_id: int
    project_name: str
    merge_request_iid: int
    merge_request_title: str
    author_name: str
    author_email: str
    status: str
    created_at: datetime | None = None


class ReviewFindingWorkbenchItem(BaseModel):
    id: int
    review_id: int
    issue_id: str = ""
    fingerprint: str
    category: str
    subcategory: str = ""
    severity: str
    confidence: float | None = None
    file_path: str = ""
    line_start: int | None = None
    line_end: int | None = None
    message: str = ""
    suggestion: str = ""
    code_snippet: str = ""
    owner_name: str | None = None
    owner_email: str | None = None
    owner: str | None = None
    is_blocking: bool = False
    is_false_positive: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    review: ReviewFindingWorkbenchReviewMeta
    latest_action: ReviewFindingActionResponse | None = None
    action_status: str = "unprocessed"


class ReviewFindingWorkbenchListResponse(BaseModel):
    count: int
    total: int
    results: list[ReviewFindingWorkbenchItem] = Field(default_factory=list)


class ReviewFindingBatchActionCreate(BaseModel):
    finding_ids: list[int] = Field(min_length=1, max_length=REVIEW_FINDING_BATCH_MAX_IDS)
    action_type: str = Field(pattern="^(fixed|ignored|todo|reopened)$")
    actor: str | None = Field(default=None, max_length=255)
    note: str = ""
    ignore_reason_code: str | None = Field(default=None, pattern=IGNORE_REASON_CODE_PATTERN)
    ignore_reason_note: str = ""


class ReviewFindingBatchActionResponse(BaseModel):
    success_count: int
    failed_count: int
    failed_ids: list[int] = Field(default_factory=list)


class ReviewFindingActionListResponse(BaseModel):
    count: int
    results: list[ReviewFindingActionResponse] = Field(default_factory=list)


class ReviewStatsBucket(BaseModel):
    name: str
    value: int


class ReviewFindingStatsResponse(BaseModel):
    total_findings: int
    by_category: list[ReviewStatsBucket] = Field(default_factory=list)
    by_severity: list[ReviewStatsBucket] = Field(default_factory=list)
    by_owner: list[ReviewStatsBucket] = Field(default_factory=list)
    daily_trend: list[dict[str, Any]] = Field(default_factory=list)
