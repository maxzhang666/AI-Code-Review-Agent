from __future__ import annotations

import pytest

from app.config import get_settings


@pytest.mark.parametrize(
    "raw_url",
    [
        '"postgresql+asyncpg://u:p@127.0.0.1:5432/db"',
        "'postgresql+asyncpg://u:p@127.0.0.1:5432/db'",
        "  postgresql+asyncpg://u:p@127.0.0.1:5432/db  ",
    ],
)
def test_database_url_is_normalized_from_environment(
    monkeypatch: pytest.MonkeyPatch,
    raw_url: str,
) -> None:
    monkeypatch.setenv("DATABASE_URL", raw_url)
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.DATABASE_URL == "postgresql+asyncpg://u:p@127.0.0.1:5432/db"
    assert settings.is_postgres is True
    assert settings.is_sqlite is False

    get_settings.cache_clear()
