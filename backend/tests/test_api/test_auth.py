from __future__ import annotations

import pytest

@pytest.mark.asyncio
async def test_login_returns_access_token(anonymous_client) -> None:
    response = await anonymous_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123456"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert isinstance(payload.get("access_token"), str)
    assert payload["access_token"]
    assert payload["user"]["username"] == "admin"


@pytest.mark.asyncio
async def test_protected_endpoint_requires_auth(anonymous_client) -> None:
    response = await anonymous_client.get("/api/system/info")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_requires_valid_token(anonymous_client) -> None:
    login_resp = await anonymous_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123456"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    me_resp = await anonymous_client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    payload = me_resp.json()
    assert payload["username"] == "admin"


@pytest.mark.asyncio
async def test_invalid_token_is_rejected(anonymous_client) -> None:
    response = await anonymous_client.get(
        "/api/system/info",
        headers={"Authorization": "Bearer invalid.token"},
    )
    assert response.status_code == 401
