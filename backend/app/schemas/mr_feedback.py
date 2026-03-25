from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MRFeedbackRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    merge_request_iid: int
    review_id: int | None = None
    issue_id: str
    rule_key: str | None = None
    action: str
    reason: str
    operator_gitlab_id: int
    operator_name: str
    operator_role: str | None = None
    source_note_id: int | None = None
    source_note_body: str
    created_at: datetime | None = None

