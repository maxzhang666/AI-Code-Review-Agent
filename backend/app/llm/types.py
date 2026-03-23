from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class LLMProtocol(str, Enum):
    openai_compatible = "openai_compatible"
    anthropic_api = "anthropic_api"
    claude_cli = "claude_cli"
    ollama_api = "ollama_api"
    mock = "mock"


class LLMRequest(BaseModel):
    prompt: str
    system_message: str | None = None
    temperature: float = 0.7
    max_tokens: int = 20480
    repo_path: str | None = None


class LLMResponse(BaseModel):
    content: str
    model: str
    usage: dict[str, Any] | None = None
    duration_ms: int
    raw_response: dict[str, Any] | None = None
