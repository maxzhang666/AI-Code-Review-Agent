from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LLMProviderCreate(BaseModel):
    name: str
    protocol: str
    is_active: bool = True
    is_default: bool = False
    config_data: dict[str, Any] = Field(default_factory=dict)


class LLMProviderUpdate(BaseModel):
    name: str | None = None
    protocol: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    config_data: dict[str, Any] | None = None


class LLMProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    protocol: str
    is_active: bool
    is_default: bool = False
    config_data: dict[str, Any] = Field(default_factory=dict)
    project_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class LLMConfigLegacyResponse(BaseModel):
    """Frontend-compatible shape matching old LLMConfig serializer."""
    id: int
    provider: str
    model: str
    max_tokens: int = 20480
    api_key: str = ""
    api_base: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None


class GitLabConfigCreate(BaseModel):
    server_url: str = "https://gitlab.com"
    private_token: str = ""
    site_url: str = ""


class GitLabConfigUpdate(BaseModel):
    server_url: str | None = None
    private_token: str | None = None
    site_url: str | None = None
    is_active: bool | None = None


class GitLabConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    server_url: str
    private_token: str
    site_url: str = ""
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FetchModelsRequest(BaseModel):
    api_base: str
    api_key: str = ""


class FetchModelsResponse(BaseModel):
    models: list[str]


class TestLLMConnectionRequest(BaseModel):
    protocol: str
    config_data: dict[str, Any] = Field(default_factory=dict)


class TestLLMConnectionResponse(BaseModel):
    success: bool
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ClaudeCliLegacyResponse(BaseModel):
    """Frontend-compatible shape matching old ClaudeCliConfig serializer."""
    id: int
    anthropic_base_url: str | None = None
    anthropic_auth_token: str = ""
    cli_path: str = "claude"
    timeout: int = 300
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
