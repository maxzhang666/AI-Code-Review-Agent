from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_admin_can_create_toggle_and_reset_user_password(client, anonymous_client) -> None:
    create_resp = await client.post(
        "/api/auth/users/",
        json={
            "username": "operator",
            "password": "operator123",
            "is_admin": False,
            "is_active": True,
        },
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    user_id = int(created["id"])
    assert created["username"] == "operator"
    assert created["is_admin"] is False
    assert created["is_active"] is True

    login_resp = await anonymous_client.post(
        "/api/auth/login",
        json={"username": "operator", "password": "operator123"},
    )
    assert login_resp.status_code == 200

    disable_resp = await client.patch(
        f"/api/auth/users/{user_id}/status",
        json={"is_active": False},
    )
    assert disable_resp.status_code == 200
    assert disable_resp.json()["is_active"] is False

    disabled_login = await anonymous_client.post(
        "/api/auth/login",
        json={"username": "operator", "password": "operator123"},
    )
    assert disabled_login.status_code == 401

    enable_resp = await client.patch(
        f"/api/auth/users/{user_id}/status",
        json={"is_active": True},
    )
    assert enable_resp.status_code == 200
    assert enable_resp.json()["is_active"] is True

    reset_resp = await client.patch(
        f"/api/auth/users/{user_id}/password",
        json={"new_password": "operator456"},
    )
    assert reset_resp.status_code == 200

    old_password_login = await anonymous_client.post(
        "/api/auth/login",
        json={"username": "operator", "password": "operator123"},
    )
    assert old_password_login.status_code == 401

    new_password_login = await anonymous_client.post(
        "/api/auth/login",
        json={"username": "operator", "password": "operator456"},
    )
    assert new_password_login.status_code == 200


@pytest.mark.asyncio
async def test_non_admin_cannot_access_user_management(client, anonymous_client) -> None:
    create_resp = await client.post(
        "/api/auth/users/",
        json={
            "username": "viewer",
            "password": "viewer123",
            "is_admin": False,
            "is_active": True,
        },
    )
    assert create_resp.status_code == 201

    login_resp = await anonymous_client.post(
        "/api/auth/login",
        json={"username": "viewer", "password": "viewer123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    list_resp = await anonymous_client.get(
        "/api/auth/users/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_resp.status_code == 403


@pytest.mark.asyncio
async def test_user_can_change_own_password(anonymous_client) -> None:
    login_resp = await anonymous_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123456"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    change_resp = await anonymous_client.post(
        "/api/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"old_password": "admin123456", "new_password": "admin654321"},
    )
    assert change_resp.status_code == 200

    old_login_resp = await anonymous_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123456"},
    )
    assert old_login_resp.status_code == 401

    new_login_resp = await anonymous_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin654321"},
    )
    assert new_login_resp.status_code == 200

