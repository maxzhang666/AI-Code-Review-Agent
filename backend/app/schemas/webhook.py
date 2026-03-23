from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WebhookLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    project_id: int
    project_name: str
    merge_request_iid: int | None = None
    user_name: str
    user_email: str
    source_branch: str
    target_branch: str
    payload: dict[str, Any] = Field(default_factory=dict)
    request_headers: dict[str, Any] = Field(default_factory=dict)
    request_body_raw: str = ""
    remote_addr: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    created_at: datetime | None = None
    processed: bool = False
    processed_at: datetime | None = None
    log_level: str = "INFO"
    skip_reason: str | None = None
    error_message: str | None = None
    pipeline_trace: dict[str, Any] = Field(default_factory=dict)
