from __future__ import annotations

from functools import partial
from typing import Any

from app.services.notification.channel_senders import ChannelSender, send_dingtalk, send_email, send_feishu, send_gitlab_channel, send_slack, send_wechat


def build_channel_sender_registry(owner: Any) -> dict[str, ChannelSender]:
    return {
        "dingtalk": partial(send_dingtalk, owner),
        "slack": partial(send_slack, owner),
        "feishu": partial(send_feishu, owner),
        "wechat": partial(send_wechat, owner),
        "email": partial(send_email, owner),
        "gitlab": partial(send_gitlab_channel, owner),
    }
