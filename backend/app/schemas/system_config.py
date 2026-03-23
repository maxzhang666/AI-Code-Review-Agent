from __future__ import annotations

from pydantic import BaseModel


class SystemConfigItem(BaseModel):
    key: str
    value: str
    description: str = ""


class SystemConfigUpdate(BaseModel):
    configs: dict[str, str]
