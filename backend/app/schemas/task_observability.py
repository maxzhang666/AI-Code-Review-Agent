from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskObservationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    run_id: str | None = None
    task_type: str
    status: str
    priority: int
    retry_count: int
    max_retries: int
    payload: dict[str, Any] = Field(default_factory=dict)
    result: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime | None = None
    duration_ms: int | None = None


class TaskEventItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: str
    run_id: str | None = None
    event_type: str
    status_after: str
    attempt_no: int
    message: str | None = None
    event_payload: dict[str, Any] | None = None
    created_at: datetime | None = None


class TaskSummaryResponse(BaseModel):
    queue_backend: str
    is_persistent: bool
    observability_persistent: bool
    by_status: dict[str, int] = Field(default_factory=dict)
    by_task_type: dict[str, int] = Field(default_factory=dict)


class TaskListResponse(BaseModel):
    count: int
    results: list[TaskObservationItem]


class TaskDetailResponse(TaskObservationItem):
    events: list[TaskEventItem] = Field(default_factory=list)
