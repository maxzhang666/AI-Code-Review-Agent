from __future__ import annotations

from app.llm.adapters.claude_cli import ClaudeCliAdapter
from app.llm.adapters.mock import MockAdapter
from app.llm.adapters.openai_compat import OpenAICompatAdapter
from app.llm.router import LLMRouter

llm_router = LLMRouter()
llm_router.register_adapter(OpenAICompatAdapter())
llm_router.register_adapter(ClaudeCliAdapter())
llm_router.register_adapter(MockAdapter())

__all__ = ["ClaudeCliAdapter", "LLMRouter", "MockAdapter", "OpenAICompatAdapter", "llm_router"]
