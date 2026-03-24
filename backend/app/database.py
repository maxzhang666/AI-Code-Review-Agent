from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import event, inspect, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_engine() -> AsyncEngine:
    settings = get_settings()
    kwargs: dict = {"echo": False}

    if settings.is_postgres:
        kwargs.update(
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800,
            pool_pre_ping=True,
        )

    engine = create_async_engine(settings.DATABASE_URL, **kwargs)

    if settings.is_sqlite:
        @event.listens_for(engine.sync_engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, _record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()

    return engine


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        yield session


async def init_db() -> None:
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_columns)

    from app.config import get_settings
    from app.services.auth import ensure_bootstrap_admin

    async with get_session_factory()() as session:
        await ensure_bootstrap_admin(session, get_settings())


# Lightweight schema migration: add missing columns to existing tables.
# create_all only creates NEW tables — it won't ALTER existing ones.
_PENDING_COLUMNS: list[tuple[str, str, str]] = [
    # (table, column, DDL suffix)
    ("gitlab_configs", "site_url", "VARCHAR(500) NOT NULL DEFAULT ''"),
    ("llm_providers", "is_default", "BOOLEAN NOT NULL DEFAULT 0"),
    ("merge_request_reviews", "review_issues", "TEXT NOT NULL DEFAULT '[]'"),
    ("merge_request_reviews", "review_summary", "TEXT NOT NULL DEFAULT ''"),
    ("merge_request_reviews", "review_highlights", "TEXT NOT NULL DEFAULT '[]'"),
    ("review_findings", "owner_name", "VARCHAR(255) NULL"),
    ("review_findings", "owner_email", "VARCHAR(255) NULL"),
    ("review_findings", "code_snippet", "TEXT NOT NULL DEFAULT ''"),
    ("webhook_logs", "pipeline_trace", "TEXT NOT NULL DEFAULT '{}'"),
]


def _migrate_columns(connection) -> None:
    insp = inspect(connection)
    for table, column, ddl in _PENDING_COLUMNS:
        if not insp.has_table(table):
            continue
        existing = {col["name"] for col in insp.get_columns(table)}
        if column not in existing:
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
