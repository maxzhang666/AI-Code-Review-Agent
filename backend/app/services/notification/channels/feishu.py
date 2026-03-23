from __future__ import annotations

import time

import httpx

from app.core.logging import get_logger
from app.services.notification.channels.base import NotificationResult, sanitize_url_for_trace, truncate_text


class FeishuService:
    def __init__(self, webhook_url: str | None, request_id: str | None = None) -> None:
        self._webhook_url = webhook_url
        self._logger = get_logger(__name__, request_id)

    async def send_text(self, text: str) -> NotificationResult:
        if not self._webhook_url:
            return {"success": False, "message": "Feishu webhook_url is not configured", "response_time": 0.0, "details": {}}

        started = time.perf_counter()
        payload = {"msg_type": "text", "content": {"text": truncate_text(text, 1500)}}
        request_payload = {
            "url": sanitize_url_for_trace(self._webhook_url),
            "method": "POST",
            "body": payload,
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(self._webhook_url, json=payload)
            elapsed = time.perf_counter() - started
            data = response.json() if response.content else {}
            success = response.status_code == 200 and data.get("code") == 0
            response_payload = {"status_code": response.status_code, "body": data}
            return {
                "success": success,
                "message": "Feishu sent" if success else f"Feishu failed: {data.get('msg', 'unknown error')}",
                "response_time": elapsed,
                "details": {
                    "status_code": response.status_code,
                    "request": request_payload,
                    "response": response_payload,
                },
            }
        except Exception as exc:
            elapsed = time.perf_counter() - started
            self._logger.log_error_with_context("feishu_send_failed", error=exc)
            return {
                "success": False,
                "message": f"Feishu exception: {exc}",
                "response_time": elapsed,
                "details": {
                    "request": request_payload,
                    "response": {"error": str(exc)},
                },
            }
