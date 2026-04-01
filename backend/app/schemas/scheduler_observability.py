from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WeeklySnapshotSchedulerLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    reason: str | None = None
    run_id: str | None = None
    task_id: str | None = None
    ignore_strategy_task_id: str | None = None
    week_start: date | None = None
    reference_date: date | None = None
    poll_seconds: int | None = None
    trigger_weekday: int | None = None
    trigger_hour: int | None = None
    use_llm: bool | None = None
    ignore_strategy_enabled: bool | None = None
    ignore_strategy_apply: bool | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class WeeklySnapshotSchedulerLogListResponse(BaseModel):
    count: int
    results: list[WeeklySnapshotSchedulerLogItem]
