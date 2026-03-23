from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LLMProvider(Base):
    __tablename__ = "llm_providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(255))
    protocol: Mapped[str] = mapped_column(sa.String(50), index=True)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, default=True, server_default=sa.true(), index=True
    )
    is_default: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false(), index=True
    )
    config_data: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), onupdate=sa.func.now()
    )

    projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="default_llm_provider"
    )


class GitLabConfig(Base):
    __tablename__ = "gitlab_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    server_url: Mapped[str] = mapped_column(
        sa.String(500), default="https://gitlab.com", server_default="https://gitlab.com"
    )
    private_token: Mapped[str] = mapped_column(sa.String(500))
    site_url: Mapped[str] = mapped_column(sa.String(500), default="", server_default="")
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, default=True, server_default=sa.true(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), onupdate=sa.func.now()
    )


# Avoid circular import at module level
from app.models.project import Project  # noqa: E402, F401
