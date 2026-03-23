from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_request_id
from app.core.logging import get_logger
from app.llm import llm_router
from app.models import GitLabConfig, LLMProvider, NotificationChannel, WebhookEventRule
from app.schemas.config import BatchUpdateConfig, ConfigSummary
from app.schemas.event_rule import WebhookEventRuleResponse
from app.schemas.llm import ClaudeCliLegacyResponse, GitLabConfigResponse, LLMConfigLegacyResponse
from app.schemas.notification import NotificationChannelResponse

router = APIRouter()


def _provider_to_legacy(provider: LLMProvider) -> LLMConfigLegacyResponse:
    config_data = provider.config_data if isinstance(provider.config_data, dict) else {}
    max_tokens_raw = config_data.get("max_tokens", 20480)
    try:
        max_tokens = int(max_tokens_raw)
    except (TypeError, ValueError):
        max_tokens = 20480
    if max_tokens <= 0:
        max_tokens = 20480
    return LLMConfigLegacyResponse(
        id=provider.id,
        provider=provider.name,
        model=str(config_data.get("model") or ""),
        max_tokens=max_tokens,
        api_key=str(config_data.get("api_key") or ""),
        api_base=(str(config_data["api_base"]) if config_data.get("api_base") else None),
        is_active=provider.is_active,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


def _provider_to_claude_legacy(provider: LLMProvider) -> ClaudeCliLegacyResponse:
    config_data = provider.config_data if isinstance(provider.config_data, dict) else {}
    timeout_raw = config_data.get("timeout", 300)
    try:
        timeout = int(timeout_raw)
    except (TypeError, ValueError):
        timeout = 300
    return ClaudeCliLegacyResponse(
        id=provider.id,
        anthropic_base_url=(str(config_data["anthropic_base_url"]) if config_data.get("anthropic_base_url") else None),
        anthropic_auth_token=str(config_data.get("anthropic_auth_token") or ""),
        cli_path=str(config_data.get("cli_path") or "claude"),
        timeout=timeout,
        is_active=provider.is_active,
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


def _channel_to_response(channel: NotificationChannel) -> NotificationChannelResponse:
    config_data = channel.config_data if isinstance(channel.config_data, dict) else {}
    return NotificationChannelResponse(
        id=channel.id,
        name=channel.name,
        notification_type=channel.notification_type,
        description=channel.description,
        is_active=channel.is_active,
        is_default=channel.is_default,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
        webhook_url=(str(config_data.get("webhook_url") or config_data.get("webhook")) if (config_data.get("webhook_url") or config_data.get("webhook")) else None),
        secret=(str(config_data.get("secret")) if config_data.get("secret") else None),
        smtp_host=(str(config_data.get("smtp_host")) if config_data.get("smtp_host") else None),
        smtp_port=(str(config_data.get("smtp_port")) if config_data.get("smtp_port") else None),
        username=(str(config_data.get("username")) if config_data.get("username") else None),
        password=(str(config_data.get("password")) if config_data.get("password") else None),
        from_email=(str(config_data.get("from_email")) if config_data.get("from_email") else None),
    )


@router.get("/configs/summary/", response_model=ConfigSummary)
async def get_config_summary(
    db: AsyncSession = Depends(get_db),
    request_id: str | None = Depends(get_request_id),
) -> ConfigSummary:
    logger = get_logger(__name__, request_id)

    providers = (
        await db.execute(select(LLMProvider).order_by(LLMProvider.updated_at.desc()))
    ).scalars().all()
    llm_provider = next((item for item in providers if item.protocol != "claude_cli"), None)
    claude_provider = next((item for item in providers if item.protocol == "claude_cli"), None)

    gitlab_config = (
        await db.execute(
            select(GitLabConfig)
            .where(GitLabConfig.is_active.is_(True))
            .order_by(GitLabConfig.updated_at.desc())
            .limit(1)
        )
    ).scalars().first()

    channels = (
        await db.execute(
            select(NotificationChannel)
            .where(NotificationChannel.notification_type != "gitlab")
            .order_by(NotificationChannel.updated_at.desc())
        )
    ).scalars().all()
    webhook_events = (await db.execute(select(WebhookEventRule).order_by(WebhookEventRule.updated_at.desc()))).scalars().all()

    logger.info(
        "config_summary_loaded",
        llm_provider_id=llm_provider.id if llm_provider else None,
        claude_provider_id=claude_provider.id if claude_provider else None,
        channels=len(channels),
        webhook_events=len(webhook_events),
    )

    return ConfigSummary(
        llm=_provider_to_legacy(llm_provider) if llm_provider else None,
        gitlab=GitLabConfigResponse.model_validate(gitlab_config, from_attributes=True) if gitlab_config else None,
        claude_cli=_provider_to_claude_legacy(claude_provider) if claude_provider else None,
        notifications=[
            {
                "id": channel.id,
                "name": channel.name,
                "type": channel.notification_type,
                "is_active": channel.is_active,
                "is_default": channel.is_default,
            }
            for channel in channels
        ],
        channels=[_channel_to_response(channel) for channel in channels],
        webhook_events=[WebhookEventRuleResponse.model_validate(rule, from_attributes=True) for rule in webhook_events],
    )


@router.post("/configs/batch_update/")
async def batch_update_configs(
    payload: BatchUpdateConfig,
    db: AsyncSession = Depends(get_db),
    request_id: str | None = Depends(get_request_id),
) -> dict[str, Any]:
    logger = get_logger(__name__, request_id)

    if payload.llm:
        llm_data = payload.llm
        provider_id = llm_data.get("id")
        provider: LLMProvider | None = None
        if provider_id:
            provider = await db.get(LLMProvider, int(provider_id))
        if provider is None:
            provider = LLMProvider(
                name=str(llm_data.get("provider") or llm_data.get("name") or "Default Provider"),
                protocol=str(llm_data.get("protocol") or "openai_compatible"),
                is_active=bool(llm_data.get("is_active", True)),
                config_data={},
            )
            db.add(provider)

        config_data = provider.config_data if isinstance(provider.config_data, dict) else {}
        config_data.update(
            {
                "model": llm_data.get("model", config_data.get("model", "")),
                "api_key": llm_data.get("api_key", config_data.get("api_key", "")),
                "api_base": llm_data.get("api_base", config_data.get("api_base")),
            }
        )
        provider.config_data = config_data
        if llm_data.get("protocol"):
            provider.protocol = str(llm_data["protocol"])
        if llm_data.get("is_active") is not None:
            provider.is_active = bool(llm_data["is_active"])

    if payload.claude_cli:
        claude_data = payload.claude_cli
        provider = (
            await db.execute(
                select(LLMProvider)
                .where(LLMProvider.protocol == "claude_cli")
                .order_by(LLMProvider.updated_at.desc())
                .limit(1)
            )
        ).scalars().first()
        if provider is None:
            provider = LLMProvider(
                name="Claude CLI",
                protocol="claude_cli",
                is_active=True,
                config_data={},
            )
            db.add(provider)

        config_data = provider.config_data if isinstance(provider.config_data, dict) else {}
        config_data.update(
            {
                "cli_path": claude_data.get("cli_path", config_data.get("cli_path", "claude")),
                "timeout": claude_data.get("timeout", config_data.get("timeout", 300)),
                "anthropic_base_url": claude_data.get("anthropic_base_url", config_data.get("anthropic_base_url")),
                "anthropic_auth_token": claude_data.get("anthropic_auth_token", config_data.get("anthropic_auth_token", "")),
            }
        )
        provider.config_data = config_data
        if claude_data.get("is_active") is not None:
            provider.is_active = bool(claude_data["is_active"])

    if payload.gitlab:
        gitlab_data = payload.gitlab
        gitlab_config = (
            await db.execute(select(GitLabConfig).order_by(GitLabConfig.updated_at.desc()).limit(1))
        ).scalars().first()
        if gitlab_config is None:
            gitlab_config = GitLabConfig(
                server_url=str(gitlab_data.get("server_url") or "https://gitlab.com"),
                private_token=str(gitlab_data.get("private_token") or ""),
                site_url=str(gitlab_data.get("site_url") or ""),
                is_active=bool(gitlab_data.get("is_active", True)),
            )
            db.add(gitlab_config)
        else:
            if gitlab_data.get("server_url") is not None:
                gitlab_config.server_url = str(gitlab_data["server_url"])
            if gitlab_data.get("private_token") is not None:
                gitlab_config.private_token = str(gitlab_data["private_token"])
            if gitlab_data.get("is_active") is not None:
                gitlab_config.is_active = bool(gitlab_data["is_active"])
            if gitlab_data.get("site_url") is not None:
                gitlab_config.site_url = str(gitlab_data["site_url"])

    await db.commit()
    logger.info("config_batch_updated")
    return {"code": 200, "message": "Batch update completed"}


@router.post("/configs/test-claude-cli/")
async def test_claude_cli(
    request: Request,
    body: dict[str, Any] | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
    request_id: str | None = Depends(get_request_id),
) -> dict[str, Any]:
    _ = request
    body = body or {}

    provider_id = body.get("provider_id")
    provider: LLMProvider | None = None
    if provider_id is not None:
        provider = await db.get(LLMProvider, int(provider_id))
        if provider is None:
            raise HTTPException(status_code=404, detail="LLM provider not found.")
    else:
        provider = (
            await db.execute(
                select(LLMProvider)
                .where(LLMProvider.protocol == "claude_cli")
                .order_by(LLMProvider.updated_at.desc())
                .limit(1)
            )
        ).scalars().first()
        if provider is None:
            raise HTTPException(status_code=404, detail="No Claude CLI provider configured.")

    ok, message = await llm_router.validate_provider(provider)
    logger = get_logger(__name__, request_id)
    logger.info("claude_cli_tested", provider_id=provider.id, ok=ok)
    return {"success": ok, "message": message or ("Configuration is valid." if ok else "Configuration is invalid.")}
