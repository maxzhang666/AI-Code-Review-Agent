from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(client) -> None:
    response = await client.get("/health/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["message"] == "Code Review GPT API v2"
