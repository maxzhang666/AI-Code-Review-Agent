from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.auth import get_current_user, require_admin
from app.core.deps import get_db, get_request_id
from app.core.logging import get_logger
from app.models import AuthUser
from app.schemas.auth import (
    AdminCreateUserRequest,
    AdminResetPasswordRequest,
    AdminUpdateUserStatusRequest,
    AdminUserProfile,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    UserProfile,
)
from app.services.auth import (
    TOKEN_TYPE,
    authenticate_user,
    create_access_token,
    ensure_bootstrap_admin,
    hash_password,
    verify_password,
    update_last_login,
    get_user_by_username,
)

router = APIRouter()


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
    request_id: str | None = Depends(get_request_id),
) -> LoginResponse:
    settings = get_settings()
    logger = get_logger(__name__, request_id)
    await ensure_bootstrap_admin(db, settings)

    user = await authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    await update_last_login(db, user)
    expires_in = max(settings.AUTH_TOKEN_EXPIRE_HOURS, 1) * 3600
    token = create_access_token(
        user_id=user.id,
        username=user.username,
        secret_key=settings.SECRET_KEY,
        expires_in_seconds=expires_in,
    )
    logger.info("auth_login_success", user_id=user.id, username=user.username)
    return LoginResponse(
        access_token=token,
        token_type=TOKEN_TYPE,
        expires_in=expires_in,
        user=UserProfile.model_validate(user, from_attributes=True),
    )


@router.post("/auth/logout")
async def logout(
    _user: AuthUser = Depends(get_current_user),
) -> dict[str, str]:
    return {"message": "Logged out"}


@router.get("/auth/me", response_model=UserProfile)
async def me(user: AuthUser = Depends(get_current_user)) -> UserProfile:
    return UserProfile.model_validate(user, from_attributes=True)


@router.post("/auth/change-password")
async def change_password(
    payload: ChangePasswordRequest,
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Old password is incorrect.")
    if payload.old_password == payload.new_password:
        raise HTTPException(status_code=400, detail="New password must be different.")

    user.password_hash = hash_password(payload.new_password)
    await db.commit()
    await db.refresh(user)
    return {"message": "Password changed successfully."}


@router.get("/auth/users/", response_model=list[AdminUserProfile])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _admin: AuthUser = Depends(require_admin),
) -> list[AdminUserProfile]:
    users = (await db.execute(select(AuthUser).order_by(AuthUser.id.asc()))).scalars().all()
    return [AdminUserProfile.model_validate(user, from_attributes=True) for user in users]


@router.post("/auth/users/", response_model=AdminUserProfile, status_code=201)
async def create_user(
    payload: AdminCreateUserRequest,
    db: AsyncSession = Depends(get_db),
    _admin: AuthUser = Depends(require_admin),
) -> AdminUserProfile:
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Username cannot be empty.")
    if await get_user_by_username(db, username):
        raise HTTPException(status_code=409, detail="Username already exists.")

    user = AuthUser(
        username=username,
        password_hash=hash_password(payload.password),
        is_admin=payload.is_admin,
        is_active=payload.is_active,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return AdminUserProfile.model_validate(user, from_attributes=True)


@router.patch("/auth/users/{user_id}/status", response_model=AdminUserProfile)
async def update_user_status(
    user_id: int,
    payload: AdminUpdateUserStatusRequest,
    db: AsyncSession = Depends(get_db),
    admin: AuthUser = Depends(require_admin),
) -> AdminUserProfile:
    user = await db.get(AuthUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.id == admin.id and not payload.is_active:
        raise HTTPException(status_code=400, detail="Cannot disable your own account.")

    user.is_active = payload.is_active
    await db.commit()
    await db.refresh(user)
    return AdminUserProfile.model_validate(user, from_attributes=True)


@router.patch("/auth/users/{user_id}/password")
async def reset_user_password(
    user_id: int,
    payload: AdminResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    _admin: AuthUser = Depends(require_admin),
) -> dict[str, Any]:
    user = await db.get(AuthUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")

    user.password_hash = hash_password(payload.new_password)
    await db.commit()
    await db.refresh(user)
    return {"message": "Password reset successfully."}
