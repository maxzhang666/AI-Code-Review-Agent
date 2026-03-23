from __future__ import annotations

import ast
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

RuleData = dict[str, Any] | list[Any]


class WebhookEventRuleCreate(BaseModel):
    name: str
    event_type: str
    description: str = ""
    match_rules: RuleData = Field(default_factory=dict)
    is_active: bool = True


class WebhookEventRuleUpdate(BaseModel):
    name: str | None = None
    event_type: str | None = None
    description: str | None = None
    match_rules: RuleData | str | None = None
    is_active: bool | None = None


class WebhookEventRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    event_type: str
    description: str = ""
    match_rules: RuleData = Field(default_factory=dict)
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("match_rules", mode="before")
    @classmethod
    def _coerce_match_rules(cls, value: Any) -> RuleData:
        if value is None:
            return {}
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return {}
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, (dict, list)):
                    return parsed
            except json.JSONDecodeError:
                pass
            try:
                parsed = ast.literal_eval(raw)
                return parsed if isinstance(parsed, (dict, list)) else {}
            except (SyntaxError, ValueError):
                return {}
        return {}
