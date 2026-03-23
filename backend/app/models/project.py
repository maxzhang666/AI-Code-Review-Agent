from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(sa.Integer, unique=True, index=True)
    project_name: Mapped[str] = mapped_column(sa.String(255))
    project_path: Mapped[str] = mapped_column(sa.String(500))
    project_url: Mapped[str] = mapped_column(sa.String(500))
    namespace: Mapped[str] = mapped_column(sa.String(255))

    review_enabled: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false(), index=True
    )
    auto_review_on_mr: Mapped[bool] = mapped_column(
        sa.Boolean, default=True, server_default=sa.true()
    )
    gitlab_comment_notifications_enabled: Mapped[bool] = mapped_column(
        sa.Boolean, default=True, server_default=sa.true()
    )

    enabled_webhook_events: Mapped[list[int]] = mapped_column(sa.JSON, default=list)
    exclude_file_types: Mapped[list[str]] = mapped_column(sa.JSON, default=list)
    ignore_file_patterns: Mapped[list[str]] = mapped_column(sa.JSON, default=list)
    gitlab_data: Mapped[dict[str, Any]] = mapped_column(sa.JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), onupdate=sa.func.now()
    )
    last_webhook_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=False), nullable=True
    )

    default_llm_provider_id: Mapped[int | None] = mapped_column(
        sa.ForeignKey("llm_providers.id", ondelete="SET NULL"), nullable=True, index=True
    )

    default_llm_provider: Mapped["LLMProvider | None"] = relationship(
        "LLMProvider", back_populates="projects", foreign_keys=[default_llm_provider_id]
    )
    notification_settings: Mapped[list[ProjectNotificationSetting]] = relationship(
        "ProjectNotificationSetting", back_populates="project", cascade="all, delete-orphan"
    )
    webhook_event_prompts: Mapped[list[ProjectWebhookEventPrompt]] = relationship(
        "ProjectWebhookEventPrompt", back_populates="project", cascade="all, delete-orphan"
    )

    def is_webhook_event_enabled(self, event_rule_id: int) -> bool:
        return event_rule_id in (self.enabled_webhook_events or [])


class ProjectNotificationSetting(Base):
    __tablename__ = "project_notification_settings"
    __table_args__ = (
        sa.UniqueConstraint("project_id", "channel_id", name="uq_proj_notif_proj_channel"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        sa.ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    channel_id: Mapped[int] = mapped_column(
        sa.ForeignKey("notification_channels.id", ondelete="CASCADE"), index=True
    )
    enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True, server_default=sa.true())
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), onupdate=sa.func.now()
    )

    project: Mapped[Project] = relationship("Project", back_populates="notification_settings")
    channel: Mapped["NotificationChannel"] = relationship(
        "NotificationChannel", back_populates="project_settings"
    )


class ProjectWebhookEventPrompt(Base):
    __tablename__ = "project_webhook_event_prompts"
    __table_args__ = (
        sa.UniqueConstraint("project_id", "event_rule_id", name="uq_proj_prompt_proj_rule"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        sa.ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    event_rule_id: Mapped[int] = mapped_column(
        sa.ForeignKey("webhook_event_rules.id", ondelete="CASCADE"), index=True
    )
    custom_prompt: Mapped[str] = mapped_column(sa.Text, default="", server_default="")
    use_custom: Mapped[bool] = mapped_column(
        sa.Boolean, default=False, server_default=sa.false()
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=False), server_default=sa.func.now(), onupdate=sa.func.now()
    )

    project: Mapped[Project] = relationship("Project", back_populates="webhook_event_prompts")
    event_rule: Mapped["WebhookEventRule"] = relationship(
        "WebhookEventRule", back_populates="project_prompts"
    )

    _PLACEHOLDERS = (
        "project_name", "project_id", "author", "title", "description",
        "source_branch", "target_branch", "mr_iid", "file_count", "changes_count",
    )

    def render_prompt(self, context: dict[str, Any]) -> str:
        if not self.custom_prompt:
            return ""
        prompt = self.custom_prompt
        for key in self._PLACEHOLDERS:
            prompt = prompt.replace(f"{{{key}}}", str(context.get(key, "")))
        return prompt


from app.models.event_rule import WebhookEventRule  # noqa: E402, F401
from app.models.llm import LLMProvider  # noqa: E402, F401
from app.models.notification import NotificationChannel  # noqa: E402, F401
