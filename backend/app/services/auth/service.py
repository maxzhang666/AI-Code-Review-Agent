from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import AuthUser
from app.services.auth.passwords import hash_password, verify_password


async def get_user_by_id(db: AsyncSession, user_id: int) -> AuthUser | None:
    return await db.get(AuthUser, user_id)


async def get_user_by_username(db: AsyncSession, username: str) -> AuthUser | None:
    normalized = username.strip().lower()
    if not normalized:
        return None
    stmt = select(AuthUser).where(func.lower(AuthUser.username) == normalized).limit(1)
    return (await db.execute(stmt)).scalars().first()


async def authenticate_user(db: AsyncSession, username: str, password: str) -> AuthUser | None:
    user = await get_user_by_username(db, username)
    if user is None or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


async def ensure_bootstrap_admin(db: AsyncSession, settings: Settings) -> AuthUser | None:
    bootstrap_username = settings.AUTH_BOOTSTRAP_USERNAME.strip()
    bootstrap_password = settings.AUTH_BOOTSTRAP_PASSWORD
    if not bootstrap_username or not bootstrap_password:
        return None

    existing_count = (
        await db.execute(select(func.count(AuthUser.id)))
    ).scalar_one()
    if int(existing_count or 0) > 0:
        return None

    user = AuthUser(
        username=bootstrap_username,
        password_hash=hash_password(bootstrap_password),
        is_active=True,
        is_admin=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_last_login(db: AsyncSession, user: AuthUser) -> None:
    user.last_login_at = datetime.now(UTC).replace(tzinfo=None)
    await db.commit()
    await db.refresh(user)
