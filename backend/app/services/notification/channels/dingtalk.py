from __future__ import annotations

import base64
import hashlib
import hmac
import time
import urllib.parse

import httpx

from app.core.logging import get_logger
from app.services.notification.channels.base import NotificationResult, sanitize_url_for_trace, truncate_text


class DingTalkService:
    def __init__(
        self,
        webhook_url: str | None,
        secret: str | None = None,
        request_id: str | None = None,
    ) -> None:
        self._webhook_url = webhook_url
        self._secret = secret
        self._logger = get_logger(__name__, request_id)

    async def send_markdown(self, title: str, content: str) -> NotificationResult:
        if not self._webhook_url:
            return {"success": False, "message": "DingTalk webhook_url is not configured", "response_time": 0.0, "details": {}}

        started = time.perf_counter()
        url = self._webhook_url
        if self._secret:
            timestamp = str(round(time.time() * 1000))
            sign = self._generate_signature(timestamp)
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}timestamp={timestamp}&sign={sign}"

        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": truncate_text(content, 1500),
            },
        }
        request_payload = {
            "url": sanitize_url_for_trace(url),
            "method": "POST",
            "body": payload,
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload)
            elapsed = time.perf_counter() - started
            data = response.json() if response.content else {}
            success = response.status_code == 200 and data.get("errcode") == 0
            response_payload = {"status_code": response.status_code, "body": data}
            return {
                "success": success,
                "message": "DingTalk sent" if success else f"DingTalk failed: {data.get('errmsg', 'unknown error')}",
                "response_time": elapsed,
                "details": {
                    "status_code": response.status_code,
                    "request": request_payload,
                    "response": response_payload,
                },
            }
        except Exception as exc:
            elapsed = time.perf_counter() - started
            self._logger.log_error_with_context("dingtalk_send_failed", error=exc)
            return {
                "success": False,
                "message": f"DingTalk exception: {exc}",
                "response_time": elapsed,
                "details": {
                    "request": request_payload,
                    "response": {"error": str(exc)},
                },
            }

    def _generate_signature(self, timestamp: str) -> str:
        if not self._secret:
            return ""
        secret_bytes = self._secret.encode("utf-8")
        to_sign = f"{timestamp}\n{self._secret}".encode("utf-8")
        digest = hmac.new(secret_bytes, to_sign, digestmod=hashlib.sha256).digest()
        return urllib.parse.quote_plus(base64.b64encode(digest))
