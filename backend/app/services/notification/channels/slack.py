from __future__ import annotations

import time
from typing import Any

import httpx

from app.core.logging import get_logger
from app.services.notification.channels.base import NotificationResult, sanitize_url_for_trace, truncate_text


class SlackService:
    def __init__(self, webhook_url: str | None, request_id: str | None = None) -> None:
        self._webhook_url = webhook_url
        self._logger = get_logger(__name__, request_id)

    async def send_message(self, text: str, blocks: list[dict[str, Any]] | None = None) -> NotificationResult:
        if not self._webhook_url:
            return {"success": False, "message": "Slack webhook_url is not configured", "response_time": 0.0, "details": {}}

        started = time.perf_counter()
        payload: dict[str, Any] = {"text": truncate_text(text, 1000)}
        if blocks:
            payload["blocks"] = blocks
        request_payload = {
            "url": sanitize_url_for_trace(self._webhook_url),
            "method": "POST",
            "body": payload,
        }
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(self._webhook_url, json=payload)
            elapsed = time.perf_counter() - started
            success = response.status_code == 200
            response_payload = {"status_code": response.status_code, "body": response.text[:400]}
            return {
                "success": success,
                "message": "Slack sent" if success else f"Slack failed: HTTP {response.status_code}",
                "response_time": elapsed,
                "details": {
                    "status_code": response.status_code,
                    "request": request_payload,
                    "response": response_payload,
                },
            }
        except Exception as exc:
            elapsed = time.perf_counter() - started
            self._logger.log_error_with_context("slack_send_failed", error=exc)
            return {
                "success": False,
                "message": f"Slack exception: {exc}",
                "response_time": elapsed,
                "details": {
                    "request": request_payload,
                    "response": {"error": str(exc)},
                },
            }
