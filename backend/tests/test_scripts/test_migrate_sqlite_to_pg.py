from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

import app.database as db_module
from app.config import get_settings
from app.database import get_session_factory, init_db
from app.models import LLMProvider, Project
from scripts.migrate_sqlite_to_pg import migrate_sqlite_to_database


async def _reset_runtime_database(monkeypatch: pytest.MonkeyPatch, database_url: str) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    get_settings.cache_clear()
    if db_module._engine is not None:
        await db_module._engine.dispose()
    db_module._engine = None
    db_module._session_factory = None


@pytest.mark.asyncio
async def test_migrate_rejects_non_postgres_target_without_explicit_override(tmp_path: Path) -> None:
    source_path = tmp_path / "source.sqlite3"
    source_path.touch()

    with pytest.raises(ValueError, match="PostgreSQL"):
        await migrate_sqlite_to_database(
            source_sqlite=source_path,
            target_url=f"sqlite+aiosqlite:///{tmp_path / 'target.sqlite3'}",
        )


@pytest.mark.asyncio
async def test_migrate_copies_rows_and_json_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_path = tmp_path / "source.sqlite3"
    source_url = f"sqlite+aiosqlite:///{source_path}"
    target_path = tmp_path / "target.sqlite3"
    target_url = f"sqlite+aiosqlite:///{target_path}"

    await _reset_runtime_database(monkeypatch, source_url)
    await init_db()
    async with get_session_factory()() as session:
        session.add(
            LLMProvider(
                id=1,
                name="default-provider",
                protocol="openai_compatible",
                is_active=True,
                is_default=True,
                config_data={"provider": "openai", "api_key": "masked"},
                created_at=datetime(2025, 1, 1, 8, 0, 0),
                updated_at=datetime(2025, 1, 1, 8, 0, 0),
            )
        )
        session.add(
            Project(
                id=1,
                project_id=123,
                project_name="demo",
                project_path="group/demo",
                project_url="https://gitlab.example.com/group/demo",
                namespace="group",
                review_enabled=True,
                auto_review_on_mr=False,
                gitlab_comment_notifications_enabled=True,
                enabled_webhook_events=[1, 2],
                exclude_file_types=[".lock"],
                ignore_file_patterns=["README.md"],
                gitlab_data={"visibility": "private"},
                default_llm_provider_id=1,
                created_at=datetime(2025, 1, 1, 9, 0, 0),
                updated_at=datetime(2025, 1, 1, 9, 0, 0),
            )
        )
        await session.commit()

    summary = await migrate_sqlite_to_database(
        source_sqlite=source_path,
        target_url=target_url,
        allow_non_postgres=True,
        truncate=True,
        batch_size=10,
    )
    assert summary["llm_providers"] == 1
    assert summary["projects"] == 1

    await _reset_runtime_database(monkeypatch, target_url)
    async with get_session_factory()() as session:
        provider = await session.get(LLMProvider, 1)
        project = await session.get(Project, 1)

    assert provider is not None
    assert provider.config_data["provider"] == "openai"
    assert provider.is_default is True
    assert project is not None
    assert project.enabled_webhook_events == [1, 2]
    assert project.gitlab_data["visibility"] == "private"
    assert project.auto_review_on_mr is False

