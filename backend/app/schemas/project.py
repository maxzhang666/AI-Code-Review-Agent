from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    project_name: str
    project_path: str
    project_url: str
    namespace: str
    review_enabled: bool
    auto_review_on_mr: bool
    gitlab_comment_notifications_enabled: bool
    enabled_webhook_events: list[int]
    exclude_file_types: list[str]
    ignore_file_patterns: list[str]
    gitlab_data: dict[str, Any]
    default_llm_provider_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_webhook_at: datetime | None = None

    # Computed fields (populated by service layer)
    commits_count: int = 0
    mr_count: int = 0
    members_count: int = 0
    last_activity: str | None = None
    weekly_reviews: int = 0
    recent_events_count: int = 0
    webhook_url: str = ""


class ProjectListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: int
    project_name: str
    namespace: str
    description: str = ""
    review_enabled: bool
    commits_count: int = 0
    mr_count: int = 0
    members_count: int = 0
    last_activity: str | None = None
    weekly_reviews: int = 0
    recent_events_count: int = 0
    webhook_url: str = ""
    created_at: datetime | None = None


class ProjectUpdate(BaseModel):
    review_enabled: bool | None = None
    auto_review_on_mr: bool | None = None
    exclude_file_types: list[str] | None = None
    ignore_file_patterns: list[str] | None = None
    gitlab_comment_notifications_enabled: bool | None = None
    default_llm_provider_id: int | None = None


class ProjectNotificationSettingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    channel_id: int
    channel_name: str = ""
    notification_type: str = ""
    enabled: bool = True


class ProjectNotificationUpdate(BaseModel):
    gitlab_comment_enabled: bool | None = None
    channel_ids: list[int] = Field(default_factory=list)


class ProjectWebhookEventPromptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project: int = Field(validation_alias=AliasChoices("project_id", "project"))
    event_rule: int = Field(validation_alias=AliasChoices("event_rule_id", "event_rule"))
    event_rule_name: str = ""
    event_rule_type: str = ""
    event_rule_description: str = ""
    custom_prompt: str = ""
    use_custom: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProjectWebhookEventPromptUpdate(BaseModel):
    event_rule_id: int
    custom_prompt: str = ""
    use_custom: bool = False


class GitLabProjectSearchItem(BaseModel):
    id: int
    name: str
    path_with_namespace: str
    web_url: str
    namespace: str
    description: str = ""
    last_activity_at: str | None = None
    imported: bool = False


class ProjectImport(BaseModel):
    project_ids: list[int]
    auto_register_webhook: bool = True


class ProjectImportResultItem(BaseModel):
    project_id: int
    name: str = ""
    success: bool = True
    webhook_registered: bool = False
    error: str | None = None
