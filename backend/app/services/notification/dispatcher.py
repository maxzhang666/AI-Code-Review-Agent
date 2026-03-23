from __future__ import annotations

import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.logging import get_logger
from app.models import NotificationChannel, Project, ProjectNotificationSetting
from app.services.notification.channel_senders import ChannelSender
from app.services.gitlab import GitLabService
from app.services.notification.channels import NotificationResult
from app.services.notification.messages import (
    build_gitlab_comment_message,
    build_html_message,
    build_markdown_message,
    build_plain_text_message,
    ensure_str_list,
    issue_location,
    issue_severity_label,
    mr_title,
    normalize_multiline,
    project_name,
)
from app.services.notification.trace import (
    build_gitlab_request_payload,
    build_gitlab_response_payload,
    is_trace_payload_empty,
    normalize_result_fields,
    normalize_trace_details,
)
from app.services.notification.registry import build_channel_sender_registry


class NotificationDispatcher:
    def __init__(self, request_id: str | None = None) -> None:
        self._settings = get_settings()
        self._request_id = request_id
        self._logger = get_logger(__name__, request_id)
        self._tz = ZoneInfo(self._settings.TIMEZONE)
        self._channel_senders: dict[str, ChannelSender] = build_channel_sender_registry(self)

    async def dispatch(
        self,
        report_data: dict[str, Any],
        mr_info: dict[str, Any],
        project_id: int | None,
        db: AsyncSession,
    ) -> dict[str, Any]:
        pid = project_id or self._extract_project_id(mr_info)
        channels, gitlab_comment_enabled = await self._get_notification_targets(pid, db)
        has_gitlab_channel = any(channel.notification_type == "gitlab" for channel in channels)

        if not channels and not gitlab_comment_enabled:
            return {
                "success": True,
                "message": "No active notification channels",
                "total_channels": 0,
                "success_channels": 0,
                "failed_channels": 0,
                "results": [],
            }

        results: list[dict[str, Any]] = []
        for channel in channels:
            result = await self._send_to_channel(channel, report_data, mr_info, db)
            results.append(
                self._build_channel_result_entry(
                    channel_id=channel.id,
                    channel_name=channel.name,
                    channel_type=channel.notification_type,
                    raw_result=result,
                    report_data=report_data,
                    mr_info=mr_info,
                )
            )

        if gitlab_comment_enabled and not has_gitlab_channel:
            gitlab_result = await self._send_to_gitlab(report_data, mr_info, db)
            gitlab_details = gitlab_result.get("details")
            gitlab_details_dict = gitlab_details if isinstance(gitlab_details, dict) else {}
            normalized_gitlab_details = self._normalize_trace_details(
                channel_type="gitlab",
                details=gitlab_details_dict,
                report_data=report_data,
                mr_info=mr_info,
            )
            results.append(
                self._build_channel_result_entry(
                    channel_id=None,
                    channel_name="GitLab Comment",
                    channel_type="gitlab",
                    raw_result=gitlab_result,
                    report_data=report_data,
                    mr_info=mr_info,
                    normalized_details=normalized_gitlab_details,
                )
            )

        if not results:
            return {
                "success": True,
                "message": "No active notification channels",
                "total_channels": 0,
                "success_channels": 0,
                "failed_channels": 0,
                "results": [],
            }

        success_count = len([item for item in results if item["success"]])
        return {
            "success": success_count > 0,
            "total_channels": len(results),
            "success_channels": success_count,
            "failed_channels": len(results) - success_count,
            "results": results,
            "dispatch_time": datetime.now(self._tz).isoformat(),
        }

    async def _get_notification_targets(
        self,
        project_id: int | None,
        db: AsyncSession,
    ) -> tuple[list[NotificationChannel], bool]:
        default_stmt = (
            select(NotificationChannel)
            .where(
                NotificationChannel.is_active.is_(True),
                NotificationChannel.is_default.is_(True),
            )
            .order_by(NotificationChannel.updated_at.desc())
        )
        default_channels = [
            channel
            for channel in (await db.execute(default_stmt)).scalars().all()
            if channel.notification_type != "gitlab"
        ]

        if project_id is None:
            return self._deduplicate_channels(default_channels), False

        project_stmt = select(Project).where(Project.project_id == project_id).limit(1)
        project = (await db.execute(project_stmt)).scalars().first()
        if project is None:
            return self._deduplicate_channels(default_channels), False

        custom_stmt = (
            select(NotificationChannel)
            .join(
                ProjectNotificationSetting,
                ProjectNotificationSetting.channel_id == NotificationChannel.id,
            )
            .where(
                ProjectNotificationSetting.project_id == project.id,
                ProjectNotificationSetting.enabled.is_(True),
                NotificationChannel.is_active.is_(True),
            )
            .order_by(NotificationChannel.updated_at.desc())
        )
        custom_channels = list((await db.execute(custom_stmt)).scalars().all())
        selected = [
            item for item in (custom_channels or default_channels)
            if item.notification_type != "gitlab"
        ]

        return self._deduplicate_channels(selected), bool(project.gitlab_comment_notifications_enabled)

    async def _send_to_channel(
        self,
        channel: NotificationChannel,
        report_data: dict[str, Any],
        mr_info: dict[str, Any],
        db: AsyncSession,
    ) -> NotificationResult:
        channel_type = channel.notification_type
        sender = self._channel_senders.get(channel_type)
        if sender is not None:
            return await sender(channel, report_data, mr_info, db)

        return {
            "success": False,
            "message": f"Unsupported channel type: {channel_type}",
            "response_time": 0.0,
            "details": {},
        }

    async def _send_to_gitlab(
        self,
        report_data: dict[str, Any],
        mr_info: dict[str, Any],
        db: AsyncSession,
    ) -> NotificationResult:
        started = time.perf_counter()
        project_id = self._extract_project_id(mr_info)
        mr_iid = self._extract_mr_iid(mr_info)
        comment = self._gitlab_comment_message(report_data, mr_info)
        request_payload = self._build_gitlab_request_payload(
            project_id=project_id,
            mr_iid=mr_iid,
            comment=comment,
        )
        if project_id is None or mr_iid is None:
            elapsed = time.perf_counter() - started
            return {
                "success": False,
                "message": "Missing project_id or mr_iid for GitLab comment",
                "response_time": elapsed,
                "details": {
                    "request": request_payload,
                    "response": {"error": "missing_project_or_mr_iid"},
                    "project_id": project_id,
                    "mr_iid": mr_iid,
                },
            }

        try:
            gitlab_service = GitLabService(db=db, request_id=self._request_id)
            result = await gitlab_service.post_merge_request_comment(
                project_id=project_id,
                mr_iid=mr_iid,
                comment=comment,
            )
            elapsed = time.perf_counter() - started
            response_payload = self._build_gitlab_response_payload(result)
            if result.get("id"):
                return {
                    "success": True,
                    "message": "GitLab comment sent",
                    "response_time": elapsed,
                    "details": {
                        "request": request_payload,
                        "response": response_payload,
                        "note_id": result.get("id"),
                    },
                }
            return {
                "success": False,
                "message": "GitLab comment failed",
                "response_time": elapsed,
                "details": {
                    "request": request_payload,
                    "response": response_payload,
                },
            }
        except Exception as exc:
            elapsed = time.perf_counter() - started
            self._logger.log_error_with_context("gitlab_notification_failed", error=exc)
            return {
                "success": False,
                "message": f"GitLab comment exception: {exc}",
                "response_time": elapsed,
                "details": {
                    "request": request_payload,
                    "response": {"error": str(exc)},
                },
            }

    def _build_channel_result_entry(
        self,
        channel_id: int | None,
        channel_name: str,
        channel_type: str,
        raw_result: NotificationResult,
        report_data: dict[str, Any],
        mr_info: dict[str, Any],
        normalized_details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        details = raw_result.get("details")
        details_dict = details if isinstance(details, dict) else {}
        final_details = normalized_details or self._normalize_trace_details(
            channel_type=channel_type,
            details=details_dict,
            report_data=report_data,
            mr_info=mr_info,
        )
        trace, error, meta = self._normalize_result_fields(raw_result, final_details)
        return {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "channel": channel_type,
            "success": bool(raw_result.get("success", False)),
            "message": raw_result.get("message", ""),
            "response_time": raw_result.get("response_time", 0.0),
            "details": final_details,
            "request": final_details.get("request"),
            "response": final_details.get("response"),
            "trace": trace,
            "error": error,
            "meta": meta,
        }

    def _normalize_result_fields(
        self,
        raw_result: NotificationResult,
        details: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]:
        return normalize_result_fields(raw_result, details)

    def _normalize_trace_details(
        self,
        channel_type: str,
        details: dict[str, Any],
        report_data: dict[str, Any],
        mr_info: dict[str, Any],
    ) -> dict[str, Any]:
        return normalize_trace_details(
            channel_type=channel_type,
            details=details,
            report_data=report_data,
            mr_info=mr_info,
            extract_project_id=self._extract_project_id,
            extract_mr_iid=self._extract_mr_iid,
            build_comment_message=self._gitlab_comment_message,
        )

    def _is_trace_payload_empty(self, payload: Any) -> bool:
        return is_trace_payload_empty(payload)

    def _build_gitlab_request_payload(
        self,
        project_id: int | None,
        mr_iid: int | None,
        comment: str,
    ) -> dict[str, Any]:
        return build_gitlab_request_payload(project_id=project_id, mr_iid=mr_iid, comment=comment)

    def _build_gitlab_response_payload(self, result: Any) -> dict[str, Any]:
        return build_gitlab_response_payload(result)

    def _deduplicate_channels(self, channels: list[NotificationChannel]) -> list[NotificationChannel]:
        ordered: dict[int, NotificationChannel] = {}
        for channel in channels:
            ordered[channel.id] = channel
        return list(ordered.values())

    def _pick_webhook(self, config: dict[str, Any]) -> str | None:
        value = config.get("webhook_url") or config.get("webhook")
        return str(value) if value else None

    def _pick_secret(self, config: dict[str, Any]) -> str | None:
        value = config.get("secret")
        return str(value) if value else None

    def _extract_project_id(self, mr_info: dict[str, Any]) -> int | None:
        value = mr_info.get("project_id")
        if isinstance(value, int):
            return value
        project = mr_info.get("project")
        if isinstance(project, dict) and isinstance(project.get("id"), int):
            return int(project["id"])
        return None

    def _extract_mr_iid(self, mr_info: dict[str, Any]) -> int | None:
        value = mr_info.get("mr_iid")
        if isinstance(value, int):
            return value
        attrs = mr_info.get("object_attributes")
        if isinstance(attrs, dict) and isinstance(attrs.get("iid"), int):
            return int(attrs["iid"])
        return None

    def _project_name(self, mr_info: dict[str, Any]) -> str:
        return project_name(mr_info)

    def _mr_title(self, mr_info: dict[str, Any]) -> str:
        return mr_title(mr_info)

    def _gitlab_comment_message(self, report_data: dict[str, Any], mr_info: dict[str, Any]) -> str:
        return build_gitlab_comment_message(report_data=report_data, mr_info=mr_info, tz=self._tz)

    def _plain_text_message(self, report_data: dict[str, Any], mr_info: dict[str, Any], limit: int) -> str:
        return build_plain_text_message(report_data=report_data, mr_info=mr_info, tz=self._tz, limit=limit)

    def _markdown_message(self, report_data: dict[str, Any], mr_info: dict[str, Any]) -> str:
        return build_markdown_message(report_data=report_data, mr_info=mr_info, tz=self._tz)

    def _html_message(self, report_data: dict[str, Any], mr_info: dict[str, Any]) -> str:
        return build_html_message(report_data=report_data, mr_info=mr_info, tz=self._tz)

    def _ensure_str_list(self, value: Any) -> list[str]:
        return ensure_str_list(value)

    def _issue_severity_label(self, severity: str) -> str:
        return issue_severity_label(severity)

    def _issue_location(self, issue: dict[str, Any]) -> str:
        return issue_location(issue)

    def _normalize_multiline(self, text: str) -> str:
        return normalize_multiline(text)
