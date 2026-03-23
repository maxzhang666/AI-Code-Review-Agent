from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_db as _get_db


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in _get_db():
        yield session


def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def get_current_settings() -> Settings:
    return get_settings()
