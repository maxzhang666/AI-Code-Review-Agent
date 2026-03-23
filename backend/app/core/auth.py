from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_db
from app.models import AuthUser
from app.services.auth import get_user_by_id, parse_access_token


def _extract_bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization") or request.headers.get("authorization")
    if not header:
        raise HTTPException(status_code=401, detail="Missing authorization header.")
    parts = header.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise HTTPException(status_code=401, detail="Invalid authorization header.")
    return parts[1].strip()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> AuthUser:
    token = _extract_bearer_token(request)
    settings = get_settings()
    try:
        payload = parse_access_token(token, secret_key=settings.SECRET_KEY)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user_id = payload.get("uid")
    if not isinstance(user_id, int):
        raise HTTPException(status_code=401, detail="Invalid token payload.")
    user = await get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive.")
    return user


def require_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin permission required.")
    return user
