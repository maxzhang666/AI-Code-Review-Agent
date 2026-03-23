from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str = "pending"
    result: dict[str, Any] | None = None
    error_message: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    priority: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
