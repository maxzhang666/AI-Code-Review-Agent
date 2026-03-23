from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    retrying = "retrying"


class TaskPriority(int, Enum):
    low = 0
    normal = 1
    high = 2
    critical = 3


class TaskPayload(BaseModel):
    task_type: str
    data: dict[str, Any] = Field(default_factory=dict)
    priority: TaskPriority = TaskPriority.normal
    max_retries: int = 3


class TaskResult(BaseModel):
    task_id: str
    status: TaskStatus
    result: dict[str, Any] | None = None
    error: str | None = None
