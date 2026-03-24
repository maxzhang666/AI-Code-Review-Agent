from __future__ import annotations

from datetime import datetime as real_datetime

import pytest

from app.models import AuthUser
from app.services.auth.passwords import hash_password
from app.services.auth.service import update_last_login


@pytest.mark.asyncio
async def test_update_last_login_persists_utc_timestamp(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services.auth import service as auth_service

    utc_stamp = real_datetime(2026, 3, 1, 1, 2, 3)
    local_stamp = real_datetime(2026, 3, 1, 9, 2, 3)

    class FakeDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ARG003
            return utc_stamp if tz is not None else local_stamp

        @classmethod
        def utcnow(cls):
            return utc_stamp

    monkeypatch.setattr(auth_service, "datetime", FakeDateTime)

    user = AuthUser(
        username="utc-user",
        password_hash=hash_password("password123"),
        is_admin=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    await update_last_login(db_session, user)

    assert user.last_login_at == utc_stamp
