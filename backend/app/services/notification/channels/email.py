from __future__ import annotations

import time
from email.message import EmailMessage

import aiosmtplib

from app.core.logging import get_logger
from app.services.notification.channels.base import NotificationResult


class EmailService:
    def __init__(
        self,
        smtp_host: str | None,
        smtp_port: int = 587,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
        request_id: str | None = None,
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._logger = get_logger(__name__, request_id)

    async def send_email(
        self,
        subject: str,
        message: str,
        html_message: str | None = None,
        from_email: str | None = None,
        to: list[str] | None = None,
        cc: list[str] | None = None,
    ) -> NotificationResult:
        recipients = list(to or [])
        cc_recipients = list(cc or [])
        recipients.extend(cc_recipients)
        if not recipients:
            return {"success": False, "message": "Email recipients are not configured", "response_time": 0.0, "details": {}}
        if not self._smtp_host:
            return {"success": False, "message": "SMTP host is not configured", "response_time": 0.0, "details": {}}

        started = time.perf_counter()
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_email or self._username or "noreply@example.com"
        msg["To"] = ", ".join(to or [])
        if cc_recipients:
            msg["Cc"] = ", ".join(cc_recipients)
        msg.set_content(message)
        if html_message:
            msg.add_alternative(html_message, subtype="html")
        request_payload = {
            "transport": "smtp",
            "smtp_host": self._smtp_host,
            "smtp_port": self._smtp_port,
            "use_tls": self._use_tls,
            "subject": subject,
            "from": from_email or self._username or "noreply@example.com",
            "to": list(to or []),
            "cc": list(cc or []),
            "recipient_count": len(recipients),
        }

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._smtp_host,
                port=self._smtp_port,
                username=self._username,
                password=self._password,
                start_tls=self._use_tls,
                timeout=30,
            )
            elapsed = time.perf_counter() - started
            return {
                "success": True,
                "message": f"Email sent to {len(recipients)} recipient(s)",
                "response_time": elapsed,
                "details": {
                    "request": request_payload,
                    "response": {"accepted": True, "recipient_count": len(recipients)},
                    "recipient_count": len(recipients),
                },
            }
        except Exception as exc:
            elapsed = time.perf_counter() - started
            self._logger.log_error_with_context("email_send_failed", error=exc)
            return {
                "success": False,
                "message": f"Email exception: {exc}",
                "response_time": elapsed,
                "details": {
                    "request": request_payload,
                    "response": {"error": str(exc)},
                },
            }
