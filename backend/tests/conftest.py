from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture()
async def test_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test.sqlite3"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path}")
    monkeypatch.setenv("TASK_QUEUE_BACKEND", "memory")
    monkeypatch.setenv("DEBUG", "true")

    from app.config import get_settings
    get_settings.cache_clear()

    import app.database as db_module

    if db_module._engine is not None:
        await db_module._engine.dispose()
    db_module._engine = None
    db_module._session_factory = None

    from app.database import init_db
    from app.main import create_app

    app = create_app()
    await init_db()
    yield app

    if db_module._engine is not None:
        await db_module._engine.dispose()
    db_module._engine = None
    db_module._session_factory = None
    get_settings.cache_clear()


@pytest_asyncio.fixture()
async def client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        login_response = await async_client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123456"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        async_client.headers.update({"Authorization": f"Bearer {token}"})
        yield async_client


@pytest_asyncio.fixture()
async def anonymous_client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


@pytest_asyncio.fixture()
async def db_session(test_app):
    from app.database import get_session_factory
    async with get_session_factory()() as session:
        yield session
