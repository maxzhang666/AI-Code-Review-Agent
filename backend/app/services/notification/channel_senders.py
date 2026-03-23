from __future__ import annotations

from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NotificationChannel
from app.services.notification.channels import DingTalkService, EmailService, FeishuService, NotificationResult, SlackService, WechatWorkService

ChannelSender = Callable[[NotificationChannel, dict[str, Any], dict[str, Any], AsyncSession], Awaitable[NotificationResult]]


async def send_dingtalk(
    owner: Any,
    channel: NotificationChannel,
    report_data: dict[str, Any],
    mr_info: dict[str, Any],
    db: AsyncSession,
) -> NotificationResult:
    _ = db
    config = channel.config_data if isinstance(channel.config_data, dict) else {}
    service = DingTalkService(
        webhook_url=owner._pick_webhook(config),
        secret=owner._pick_secret(config),
        request_id=owner._request_id,
    )
    title = f"AI代码审查报告 - {owner._mr_title(mr_info)}"
    content = owner._markdown_message(report_data, mr_info)
    return await service.send_markdown(title, content)


async def send_slack(
    owner: Any,
    channel: NotificationChannel,
    report_data: dict[str, Any],
    mr_info: dict[str, Any],
    db: AsyncSession,
) -> NotificationResult:
    _ = db
    config = channel.config_data if isinstance(channel.config_data, dict) else {}
    service = SlackService(owner._pick_webhook(config), request_id=owner._request_id)
    text = owner._plain_text_message(report_data, mr_info, limit=1000)
    return await service.send_message(text=text)


async def send_feishu(
    owner: Any,
    channel: NotificationChannel,
    report_data: dict[str, Any],
    mr_info: dict[str, Any],
    db: AsyncSession,
) -> NotificationResult:
    _ = db
    config = channel.config_data if isinstance(channel.config_data, dict) else {}
    service = FeishuService(owner._pick_webhook(config), request_id=owner._request_id)
    text = owner._plain_text_message(report_data, mr_info, limit=1500)
    return await service.send_text(text)


async def send_wechat(
    owner: Any,
    channel: NotificationChannel,
    report_data: dict[str, Any],
    mr_info: dict[str, Any],
    db: AsyncSession,
) -> NotificationResult:
    _ = db
    config = channel.config_data if isinstance(channel.config_data, dict) else {}
    service = WechatWorkService(owner._pick_webhook(config), request_id=owner._request_id)
    text = owner._plain_text_message(report_data, mr_info, limit=1500)
    return await service.send_text(text)


async def send_email(
    owner: Any,
    channel: NotificationChannel,
    report_data: dict[str, Any],
    mr_info: dict[str, Any],
    db: AsyncSession,
) -> NotificationResult:
    _ = db
    config = channel.config_data if isinstance(channel.config_data, dict) else {}
    smtp_port_raw = config.get("smtp_port", 587)
    try:
        smtp_port = int(smtp_port_raw)
    except (TypeError, ValueError):
        smtp_port = 587

    service = EmailService(
        smtp_host=str(config.get("smtp_host") or ""),
        smtp_port=smtp_port,
        username=str(config.get("username") or ""),
        password=str(config.get("password") or ""),
        use_tls=bool(config.get("use_tls", True)),
        request_id=owner._request_id,
    )
    subject = f"AI代码审查报告 - {owner._project_name(mr_info)} - {owner._mr_title(mr_info)}"
    plain = owner._plain_text_message(report_data, mr_info, limit=20000)
    html = owner._html_message(report_data, mr_info)
    to = owner._ensure_str_list(config.get("to"))
    cc = owner._ensure_str_list(config.get("cc"))
    from_email = str(config.get("from_email") or "")
    return await service.send_email(
        subject=subject,
        message=plain,
        html_message=html,
        from_email=from_email or None,
        to=to,
        cc=cc,
    )


async def send_gitlab_channel(
    owner: Any,
    channel: NotificationChannel,
    report_data: dict[str, Any],
    mr_info: dict[str, Any],
    db: AsyncSession,
) -> NotificationResult:
    _ = channel
    return await owner._send_to_gitlab(report_data, mr_info, db)
