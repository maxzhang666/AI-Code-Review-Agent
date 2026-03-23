from __future__ import annotations

from time import perf_counter
from typing import Any

from app.llm.base import ProtocolAdapter
from app.llm.types import LLMProtocol, LLMRequest, LLMResponse


class MockAdapter(ProtocolAdapter):
    @classmethod
    def protocol(cls) -> LLMProtocol:
        return LLMProtocol.mock

    async def validate(self, config: dict[str, Any]) -> tuple[bool, str | None]:
        return True, None

    async def review(self, request: LLMRequest, config: dict[str, Any]) -> LLMResponse:
        started = perf_counter()
        content = (
            "### \U0001f600代码评分:85\n\n"
            "#### \u2705代码优点:\n"
            "- 代码结构清晰，职责划分明确。\n\n"
            "#### \U0001f914问题点:\n"
            "- 缺少关键路径异常处理。\n\n"
            "#### \U0001f3af修改建议:\n"
            "- 为外部依赖调用增加超时与重试。\n\n"
            "#### \U0001f4bb修改后的代码:\n"
            "```python\n# mock response\n```"
        )
        return LLMResponse(
            content=content,
            model=str(config.get("model", "mock-model")),
            usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            duration_ms=int((perf_counter() - started) * 1000),
            raw_response={"request_prompt_preview": request.prompt[:200]},
        )
