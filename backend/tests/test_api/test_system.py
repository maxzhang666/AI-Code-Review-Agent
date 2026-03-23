from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_system_info_uses_system_timezone_not_env_config(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api import system as system_api

    class _FakeSettings:
        TIMEZONE = "Fake/Timezone"
        DEBUG = True
        DATABASE_URL = "sqlite+aiosqlite:///./db.sqlite3"

    monkeypatch.setattr(system_api, "get_settings", lambda: _FakeSettings())

    response = await client.get("/api/system/info")
    assert response.status_code == 200
    payload = response.json()
    assert payload["timezone"] != "Fake/Timezone"


@pytest.mark.asyncio
async def test_system_info_includes_database_type(client) -> None:
    response = await client.get("/api/system/info")
    assert response.status_code == 200
    payload = response.json()
    assert payload["databaseType"] == "sqlite"
