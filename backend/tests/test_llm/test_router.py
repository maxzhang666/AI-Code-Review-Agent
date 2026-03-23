from __future__ import annotations

import pytest

from app.llm.adapters.mock import MockAdapter
from app.llm.router import LLMRouter
from app.llm.types import LLMProtocol, LLMRequest
from app.models import LLMProvider


@pytest.mark.asyncio
async def test_router_dispatches_to_mock_adapter() -> None:
    router = LLMRouter()
    router.register_adapter(MockAdapter())

    provider = LLMProvider(
        name="mock-provider",
        protocol=LLMProtocol.mock.value,
        is_active=True,
        config_data={"model": "mock-model-for-test"},
    )
    response = await router.review(provider, LLMRequest(prompt="review this diff"))
    assert response.model == "mock-model-for-test"
    assert "代码评分" in response.content


@pytest.mark.asyncio
async def test_router_validate_provider_success() -> None:
    router = LLMRouter()
    router.register_adapter(MockAdapter())

    provider = LLMProvider(name="mock", protocol=LLMProtocol.mock.value, is_active=True, config_data={})
    ok, error = await router.validate_provider(provider)
    assert ok is True
    assert error is None


@pytest.mark.asyncio
async def test_router_missing_adapter_raises() -> None:
    router = LLMRouter()
    provider = LLMProvider(name="openai", protocol=LLMProtocol.openai_compatible.value, is_active=True, config_data={})
    with pytest.raises(RuntimeError):
        await router.review(provider, LLMRequest(prompt="hello"))
