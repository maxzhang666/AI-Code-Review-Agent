from __future__ import annotations

import ast
import json
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WebhookEventRule(Base):
    __tablename__ = "webhook_event_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(255))
    event_type: Mapped[str] = mapped_column(sa.String(100), index=True)
    description: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
    match_rules: Mapped[dict[str, Any] | str] = mapped_column(sa.JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, default=True, server_default=sa.true(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), onupdate=sa.func.now()
    )

    project_prompts: Mapped[list["ProjectWebhookEventPrompt"]] = relationship(
        "ProjectWebhookEventPrompt", back_populates="event_rule", cascade="all, delete-orphan"
    )

    @property
    def match_rules_dict(self) -> dict[str, Any]:
        raw = self.match_rules
        if isinstance(raw, dict):
            return raw
        if raw is None:
            return {}
        if isinstance(raw, str):
            val = raw.strip()
            if not val:
                return {}
            try:
                parsed = json.loads(val)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
            try:
                parsed = ast.literal_eval(val)
                if isinstance(parsed, dict):
                    return parsed
            except (SyntaxError, ValueError):
                pass
        return {}

    def matches_payload(self, payload: dict[str, Any]) -> bool:
        if not self.is_active or not payload:
            return False
        rules = self.match_rules_dict
        if not rules:
            return False
        return self._deep_match(rules, payload)

    def _deep_match(self, rules: dict, data: dict) -> bool:
        for key, value in rules.items():
            if key not in data:
                return False
            if isinstance(value, dict) and isinstance(data[key], dict):
                if not self._deep_match(value, data[key]):
                    return False
            elif data[key] != value:
                return False
        return True


from app.models.project import ProjectWebhookEventPrompt  # noqa: E402, F401
