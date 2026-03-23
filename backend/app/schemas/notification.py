from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

NotificationChannelType = Literal["dingtalk", "email", "slack", "feishu", "wechat"]


class NotificationChannelCreate(BaseModel):
    name: str
    notification_type: NotificationChannelType
    description: str = ""
    is_active: bool = True
    is_default: bool = False
    config_data: dict[str, Any] = Field(default_factory=dict)


class NotificationChannelUpdate(BaseModel):
    name: str | None = None
    notification_type: NotificationChannelType | None = None
    description: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    config_data: dict[str, Any] | None = None


class NotificationChannelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    notification_type: str
    description: str = ""
    is_active: bool = True
    is_default: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # Flattened config fields (populated by API layer per notification_type)
    webhook_url: str | None = None
    secret: str | None = None
    smtp_host: str | None = None
    smtp_port: str | None = None
    username: str | None = None
    password: str | None = None
    from_email: str | None = None
