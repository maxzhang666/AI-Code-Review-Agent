from __future__ import annotations

from app.schemas.common import ErrorResponse, PaginatedResponse, SuccessResponse
from app.schemas.config import BatchUpdateConfig, ConfigSummary
from app.schemas.event_rule import (
    WebhookEventRuleCreate,
    WebhookEventRuleResponse,
    WebhookEventRuleUpdate,
)
from app.schemas.llm import (
    ClaudeCliLegacyResponse,
    GitLabConfigCreate,
    GitLabConfigResponse,
    GitLabConfigUpdate,
    LLMConfigLegacyResponse,
    LLMProviderCreate,
    LLMProviderResponse,
    LLMProviderUpdate,
)
from app.schemas.notification import (
    NotificationChannelCreate,
    NotificationChannelResponse,
    NotificationChannelUpdate,
)
from app.schemas.mr_feedback import MRFeedbackRecordResponse
from app.schemas.project import (
    GitLabProjectSearchItem,
    ProjectImport,
    ProjectImportResultItem,
    ProjectListResponse,
    ProjectNotificationSettingResponse,
    ProjectNotificationUpdate,
    ProjectResponse,
    ProjectUpdate,
    ProjectWebhookEventPromptResponse,
    ProjectWebhookEventPromptUpdate,
)
from app.schemas.queue import TaskRecordResponse
from app.schemas.review import MergeRequestReviewResponse
from app.schemas.system_config import SystemConfigItem, SystemConfigUpdate
from app.schemas.webhook import WebhookLogResponse

__all__ = [
    "BatchUpdateConfig",
    "ClaudeCliLegacyResponse",
    "ConfigSummary",
    "ErrorResponse",
    "GitLabConfigCreate",
    "GitLabConfigResponse",
    "GitLabConfigUpdate",
    "GitLabProjectSearchItem",
    "LLMConfigLegacyResponse",
    "LLMProviderCreate",
    "LLMProviderResponse",
    "LLMProviderUpdate",
    "MergeRequestReviewResponse",
    "MRFeedbackRecordResponse",
    "NotificationChannelCreate",
    "NotificationChannelResponse",
    "NotificationChannelUpdate",
    "PaginatedResponse",
    "ProjectImport",
    "ProjectImportResultItem",
    "ProjectListResponse",
    "ProjectNotificationSettingResponse",
    "ProjectNotificationUpdate",
    "ProjectResponse",
    "ProjectUpdate",
    "ProjectWebhookEventPromptResponse",
    "ProjectWebhookEventPromptUpdate",
    "SuccessResponse",
    "SystemConfigItem",
    "SystemConfigUpdate",
    "TaskRecordResponse",
    "WebhookEventRuleCreate",
    "WebhookEventRuleResponse",
    "WebhookEventRuleUpdate",
    "WebhookLogResponse",
]
