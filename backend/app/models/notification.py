from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class NotificationChannel(Base):
    __tablename__ = "notification_channels"
    __table_args__ = (
        sa.CheckConstraint(
            "notification_type IN ('dingtalk','gitlab','email','slack','feishu','wechat')",
            name="ck_notification_channels_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(255))
    notification_type: Mapped[str] = mapped_column(sa.String(50), index=True)
    description: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
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

    project_settings: Mapped[list["ProjectNotificationSetting"]] = relationship(
        "ProjectNotificationSetting", back_populates="channel", cascade="all, delete-orphan"
    )


from app.models.project import ProjectNotificationSetting  # noqa: E402, F401
