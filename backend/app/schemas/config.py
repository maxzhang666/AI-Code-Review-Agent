from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.schemas.llm import (
    ClaudeCliLegacyResponse,
    GitLabConfigResponse,
    LLMConfigLegacyResponse,
)
from app.schemas.notification import NotificationChannelResponse
from app.schemas.event_rule import WebhookEventRuleResponse


class ConfigSummary(BaseModel):
    llm: LLMConfigLegacyResponse | None = None
    gitlab: GitLabConfigResponse | None = None
    claude_cli: ClaudeCliLegacyResponse | None = None
    notifications: list[Any] = Field(default_factory=list)
    channels: list[NotificationChannelResponse] = Field(default_factory=list)
    webhook_events: list[WebhookEventRuleResponse] = Field(default_factory=list)


class BatchUpdateConfig(BaseModel):
    llm: dict[str, Any] | None = None
    gitlab: dict[str, Any] | None = None
    claude_cli: dict[str, Any] | None = None
