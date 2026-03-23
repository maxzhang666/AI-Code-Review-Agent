from __future__ import annotations

import pytest

from app.llm.types import LLMResponse


@pytest.mark.asyncio
async def test_llm_provider_connection_openai_success(client, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_validate_provider(provider):
        _ = provider
        return True, None

    async def _fake_review(provider, request):
        assert provider.protocol == "openai_compatible"
        assert provider.config_data.get("model") == "gpt-5"
        assert "CONNECTION_OK" in request.prompt
        return LLMResponse(
            content="CONNECTION_OK",
            model="gpt-5",
            usage={"prompt_tokens": 12, "completion_tokens": 3, "total_tokens": 15},
            duration_ms=88,
            raw_response={"id": "test-id"},
        )

    monkeypatch.setattr("app.api.llm.llm_router.validate_provider", _fake_validate_provider)
    monkeypatch.setattr("app.api.llm.llm_router.review", _fake_review)

    response = await client.post(
        "/api/llm-configs/test-connection/",
        json={
            "protocol": "openai_compatible",
            "config_data": {
                "api_base": "https://example.test/v1",
                "api_key": "sk-test",
                "model": "gpt-5",
                "timeout": 20,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["details"]["protocol"] == "openai_compatible"
    assert payload["details"]["model"] == "gpt-5"
    assert payload["details"]["content"] == "CONNECTION_OK"
    assert payload["details"]["content_length"] == len("CONNECTION_OK")
    assert payload["details"]["raw_response"] == {"id": "test-id"}


@pytest.mark.asyncio
async def test_llm_provider_connection_request_failed(client, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_validate_provider(provider):
        _ = provider
        return True, None

    async def _fake_review(provider, request):
        _ = provider, request
        raise RuntimeError("401 unauthorized")

    monkeypatch.setattr("app.api.llm.llm_router.validate_provider", _fake_validate_provider)
    monkeypatch.setattr("app.api.llm.llm_router.review", _fake_review)

    response = await client.post(
        "/api/llm-configs/test-connection/",
        json={
            "protocol": "openai_compatible",
            "config_data": {
                "api_base": "https://example.test/v1",
                "model": "gpt-5",
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["message"] == "模型调用失败: 401 unauthorized"


@pytest.mark.asyncio
async def test_llm_provider_connection_claude_cli_validation_error(client) -> None:
    response = await client.post(
        "/api/llm-configs/test-connection/",
        json={
            "protocol": "claude_cli",
            "config_data": {
                "cli_path": "definitely-not-installed-claude-cli",
                "timeout": 300,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert "CLI executable not found" in payload["message"]


@pytest.mark.asyncio
async def test_llm_provider_connection_mock_success(client) -> None:
    response = await client.post(
        "/api/llm-configs/test-connection/",
        json={
            "protocol": "mock",
            "config_data": {},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["details"]["protocol"] == "mock"
    assert payload["details"]["content_length"] > 0
    assert isinstance(payload["details"]["raw_response"], dict)
