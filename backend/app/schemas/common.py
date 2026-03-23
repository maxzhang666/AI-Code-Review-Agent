from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class SuccessResponse(BaseModel):
    code: int = 200
    message: str = "ok"


class ErrorResponse(BaseModel):
    code: int
    message: str
    errors: Any = None


class PaginatedResponse(BaseModel, Generic[T]):
    count: int
    results: list[T]
    page: int = 1
    page_size: int = 100


class DateTimeMixin(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.strftime(DATETIME_FORMAT) if v else None},
    )
