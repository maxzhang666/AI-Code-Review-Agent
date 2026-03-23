from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.llm.types import LLMProtocol, LLMRequest, LLMResponse


class ProtocolAdapter(ABC):
    @classmethod
    @abstractmethod
    def protocol(cls) -> LLMProtocol:
        raise NotImplementedError

    @abstractmethod
    async def review(self, request: LLMRequest, config: dict[str, Any]) -> LLMResponse:
        raise NotImplementedError

    @abstractmethod
    async def validate(self, config: dict[str, Any]) -> tuple[bool, str | None]:
        raise NotImplementedError
