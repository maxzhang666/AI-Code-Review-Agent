from __future__ import annotations

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.llm.base import ProtocolAdapter
from app.llm.types import LLMProtocol, LLMRequest, LLMResponse
from app.models import LLMProvider, Project


class LLMRouter:
    def __init__(self) -> None:
        self._adapters: dict[LLMProtocol, ProtocolAdapter] = {}

    def register_adapter(self, adapter: ProtocolAdapter) -> None:
        self._adapters[adapter.protocol()] = adapter

    async def resolve_provider(self, project_id: int, db: AsyncSession) -> LLMProvider:
        stmt = (
            select(Project)
            .options(selectinload(Project.default_llm_provider))
            .where(Project.project_id == project_id)
            .limit(1)
        )
        project = (await db.execute(stmt)).scalars().first()
        if project and project.default_llm_provider and project.default_llm_provider.is_active:
            return project.default_llm_provider

        # Fallback: is_default provider
        default_provider = (
            await db.execute(
                select(LLMProvider)
                .where(LLMProvider.is_default.is_(True), LLMProvider.is_active.is_(True))
                .limit(1)
            )
        ).scalars().first()
        if default_provider is not None:
            return default_provider

        # Last resort: first active provider
        fallback = (
            select(LLMProvider)
            .where(LLMProvider.is_active.is_(True))
            .order_by(LLMProvider.id.asc())
            .limit(1)
        )
        provider = (await db.execute(fallback)).scalars().first()
        if provider is None:
            raise RuntimeError("No active LLM provider configured.")
        return provider

    async def review(self, provider: LLMProvider, request: LLMRequest) -> LLMResponse:
        protocol = LLMProtocol(provider.protocol)
        adapter = self._adapters.get(protocol)
        if adapter is None:
            raise RuntimeError(f"No adapter for protocol: {provider.protocol}")
        config = cast(dict, provider.config_data or {})
        return await adapter.review(request, config)

    async def validate_provider(self, provider: LLMProvider) -> tuple[bool, str | None]:
        try:
            protocol = LLMProtocol(provider.protocol)
        except ValueError:
            return False, f"Unsupported protocol: {provider.protocol}"
        adapter = self._adapters.get(protocol)
        if adapter is None:
            return False, f"No adapter for protocol: {provider.protocol}"
        return await adapter.validate(cast(dict, provider.config_data or {}))
