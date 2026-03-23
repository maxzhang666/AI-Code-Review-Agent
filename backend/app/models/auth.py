from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuthUser(Base):
    __tablename__ = "auth_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(sa.String(128), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(sa.String(512))
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, default=True, server_default=sa.true(), index=True
    )
    is_admin: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false(), index=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), onupdate=sa.func.now()
    )

