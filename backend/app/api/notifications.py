from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.core.deps import get_db, get_request_id
from app.core.logging import get_logger
from app.models import NotificationChannel
from app.schemas.notification import NotificationChannelCreate, NotificationChannelResponse, NotificationChannelUpdate
from app.services.gitlab import GitLabService
from app.services.notification import DingTalkService, EmailService, FeishuService, SlackService, WechatWorkService

router = APIRouter()


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


def _pick_webhook(config_data: dict[str, Any]) -> str | None:
    value = config_data.get("webhook_url") or config_data.get("webhook")
    return str(value) if value else None


def _to_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


async def _get_channel_or_404(channel_id: int, db: AsyncSession) -> NotificationChannel:
    channel = await db.get(NotificationChannel, channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Notification channel not found.")
    return channel


@router.get("/notification-channels/")
async def list_notification_channels(
    page: int = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    settings = get_settings()
    page_size = settings.PAGE_SIZE
    offset = (page - 1) * page_size

    count = len((
        await db.execute(
            select(NotificationChannel.id).where(NotificationChannel.notification_type != "gitlab")
        )
    ).all())
    channels = (
        await db.execute(
            select(NotificationChannel)
            .where(NotificationChannel.notification_type != "gitlab")
            .order_by(NotificationChannel.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).scalars().all()
    return {"count": count, "results": [_channel_to_response(channel) for channel in channels]}


@router.post("/notification-channels/", response_model=NotificationChannelResponse)
async def create_notification_channel(
    payload: NotificationChannelCreate,
    db: AsyncSession = Depends(get_db),
) -> NotificationChannelResponse:
    channel = NotificationChannel(
        name=payload.name,
        notification_type=payload.notification_type,
        description=payload.description,
        is_active=payload.is_active,
        is_default=payload.is_default,
        config_data=payload.config_data,
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return _channel_to_response(channel)


@router.get("/notification-channels/{channel_id}/", response_model=NotificationChannelResponse)
async def get_notification_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
) -> NotificationChannelResponse:
    channel = await _get_channel_or_404(channel_id, db)
    return _channel_to_response(channel)


@router.put("/notification-channels/{channel_id}/", response_model=NotificationChannelResponse)
async def put_notification_channel(
    channel_id: int,
    payload: NotificationChannelCreate,
    db: AsyncSession = Depends(get_db),
) -> NotificationChannelResponse:
    channel = await _get_channel_or_404(channel_id, db)
    channel.name = payload.name
    channel.notification_type = payload.notification_type
    channel.description = payload.description
    channel.is_active = payload.is_active
    channel.is_default = payload.is_default
    channel.config_data = payload.config_data
    await db.commit()
    await db.refresh(channel)
    return _channel_to_response(channel)


@router.patch("/notification-channels/{channel_id}/", response_model=NotificationChannelResponse)
async def patch_notification_channel(
    channel_id: int,
    payload: NotificationChannelUpdate,
    db: AsyncSession = Depends(get_db),
) -> NotificationChannelResponse:
    channel = await _get_channel_or_404(channel_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(channel, field, value)
    await db.commit()
    await db.refresh(channel)
    return _channel_to_response(channel)


@router.delete("/notification-channels/{channel_id}/")
async def delete_notification_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    channel = await _get_channel_or_404(channel_id, db)
    await db.delete(channel)
    await db.commit()
    return {"code": 200, "message": "Notification channel deleted"}


@router.post("/notification-channels/{channel_id}/test/")
async def test_notification_channel(
    channel_id: int,
    body: dict[str, Any] = Body(default_factory=dict),
    db: AsyncSession = Depends(get_db),
    request_id: str | None = Depends(get_request_id),
) -> dict[str, Any]:
    settings = get_settings()
    logger = get_logger(__name__, request_id)
    channel = await _get_channel_or_404(channel_id, db)
    config_data = channel.config_data if isinstance(channel.config_data, dict) else {}

    now = datetime.now(ZoneInfo(settings.TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
    report_text = str(body.get("report") or "This is a test notification.")
    project_name = str(body.get("project_name") or "Test Project")
    mr_title = str(body.get("mr_title") or "Test Merge Request")
    sample_message = (
        "🤖 AI Code Review Report (Test)\n\n"
        f"Project: {project_name}\n"
        f"MR: {mr_title}\n"
        f"Time: {now}\n\n"
        f"{report_text}"
    )

    if channel.notification_type == "dingtalk":
        service = DingTalkService(
            webhook_url=_pick_webhook(config_data),
            secret=(str(config_data.get("secret")) if config_data.get("secret") else None),
            request_id=request_id,
        )
        result = await service.send_markdown("AI Review Test", sample_message)
        return {"channel": "dingtalk", **result}

    if channel.notification_type == "slack":
        service = SlackService(webhook_url=_pick_webhook(config_data), request_id=request_id)
        result = await service.send_message(sample_message)
        return {"channel": "slack", **result}

    if channel.notification_type == "feishu":
        service = FeishuService(webhook_url=_pick_webhook(config_data), request_id=request_id)
        result = await service.send_text(sample_message)
        return {"channel": "feishu", **result}

    if channel.notification_type == "wechat":
        service = WechatWorkService(webhook_url=_pick_webhook(config_data), request_id=request_id)
        result = await service.send_text(sample_message)
        return {"channel": "wechat", **result}

    if channel.notification_type == "email":
        smtp_port_raw = config_data.get("smtp_port", 587)
        try:
            smtp_port = int(smtp_port_raw)
        except (TypeError, ValueError):
            smtp_port = 587
        service = EmailService(
            smtp_host=(str(config_data.get("smtp_host")) if config_data.get("smtp_host") else None),
            smtp_port=smtp_port,
            username=(str(config_data.get("username")) if config_data.get("username") else None),
            password=(str(config_data.get("password")) if config_data.get("password") else None),
            use_tls=bool(config_data.get("use_tls", True)),
            request_id=request_id,
        )
        result = await service.send_email(
            subject="AI Review Test",
            message=sample_message,
            html_message=f"<pre>{sample_message}</pre>",
            from_email=(str(config_data.get("from_email")) if config_data.get("from_email") else None),
            to=_to_str_list(config_data.get("to")),
            cc=_to_str_list(config_data.get("cc")),
        )
        return {"channel": "email", **result}

    if channel.notification_type == "gitlab":
        project_id = body.get("project_id")
        mr_iid = body.get("mr_iid")
        if not isinstance(project_id, int) or not isinstance(mr_iid, int):
            raise HTTPException(
                status_code=400,
                detail="project_id and mr_iid are required to test gitlab channel.",
            )

        service = GitLabService(db=db, request_id=request_id)
        try:
            result = await service.post_merge_request_comment(project_id, mr_iid, sample_message)
        except Exception as exc:
            logger.log_error_with_context("gitlab_notification_test_failed", error=exc)
            return {
                "channel": "gitlab",
                "success": False,
                "message": f"GitLab test failed: {exc}",
                "response_time": 0.0,
                "details": {"error": str(exc)},
            }
        return {
            "channel": "gitlab",
            "success": bool(result.get("id")),
            "message": "GitLab comment sent" if result.get("id") else "GitLab comment failed",
            "response_time": 0.0,
            "details": result,
        }

    raise HTTPException(status_code=400, detail=f"Unsupported notification type: {channel.notification_type}")
