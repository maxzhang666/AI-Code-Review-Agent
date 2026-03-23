from __future__ import annotations

import json

import pytest

from app.models import LLMProvider, Project, WebhookEventRule, WebhookLog
from app.database import get_session_factory
from app.queue.tasks import review_merge_request


@pytest.mark.asyncio
async def test_review_pipeline_trace_contains_change_filter_step(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = LLMProvider(
        name="openai-provider",
        protocol="openai_compatible",
        is_active=True,
        is_default=True,
        config_data={"model": "gpt-5", "api_base": "http://llm.local/v1", "api_key": "sk-test", "timeout": 60},
    )
    db_session.add(provider)
    await db_session.flush()

    event_rule = WebhookEventRule(
        name="MR Rule",
        event_type="Merge Request Hook",
        description="",
        match_rules={"object_kind": "merge_request"},
        is_active=True,
    )
    db_session.add(event_rule)
    await db_session.flush()

    project = Project(
        project_id=3001,
        project_name="trace-demo",
        project_path="group/trace-demo",
        project_url="https://gitlab.example.com/group/trace-demo.git",
        namespace="group",
        review_enabled=True,
        enabled_webhook_events=[event_rule.id],
        default_llm_provider_id=provider.id,
    )
    db_session.add(project)
    await db_session.flush()

    webhook_log = WebhookLog(
        event_type="Merge Request Hook",
        project_id=project.project_id,
        project_name=project.project_name,
        merge_request_iid=23,
        user_name="Bob",
        user_email="bob@example.com",
        source_branch="feature/filter",
        target_branch="main",
        payload={},
        request_headers={},
        request_body_raw="{}",
        request_id="req-3001",
    )
    db_session.add(webhook_log)
    await db_session.commit()

    async def fake_get_changes(self, project_id: int, mr_iid: int):  # noqa: ANN001
        _ = self, project_id, mr_iid
        return {
            "changes": [
                {"new_path": "src/A.java", "diff": "+a"},
                {"new_path": "src/B.java", "diff": "+b"},
                {"new_path": "src/CGenerated.java", "diff": "+c"},
            ]
        }

    async def fake_review_merge_request(self, changes, payload, db):  # noqa: ANN001
        _ = self, changes, payload, db
        return {
            "content": "ok",
            "score": 86,
            "summary": "ok",
            "issues": [{"severity": "low", "category": "质量", "file": "src/A.java", "line": 1, "description": "x", "suggestion": "y"}],
            "highlights": ["h1"],
            "files_reviewed": ["src/A.java", "src/B.java"],
            "llm_model": "gpt-5-2025-08-07",
            "llm_trace": {
                "request": {
                    "provider": "openai-provider",
                    "protocol": "openai_compatible",
                    "model": "gpt-5-2025-08-07",
                    "prompt_length": 1024,
                    "prompt_preview": "diff preview",
                    "prompt_preview_truncated": False,
                    "system_message_length": 80,
                    "system_message_preview": "system prompt",
                    "system_message_preview_truncated": False,
                },
                "response": {
                    "model": "gpt-5-2025-08-07",
                    "duration_ms": 998,
                    "content_length": 512,
                    "content_preview": "{\"score\": 86}",
                    "content_preview_truncated": False,
                },
            },
            "filter_summary": {
                "raw_file_count": 3,
                "filtered_file_count": 2,
                "removed_file_count": 1,
                "excluded_by_type_count": 0,
                "ignored_by_pattern_count": 1,
                "deleted_file_count": 0,
                "renamed_without_diff_count": 0,
            },
        }

    async def fake_dispatch(self, report_data, mr_info, project_id, db):  # noqa: ANN001
        _ = self, report_data, mr_info, project_id, db
        return {
            "success": True,
            "total_channels": 2,
            "success_channels": 1,
            "failed_channels": 1,
            "results": [
                {
                    "channel_id": 1,
                    "channel_name": "Slack Main",
                    "channel": "slack",
                    "success": True,
                    "message": "Slack sent",
                    "response_time": 0.23,
                    "details": {"status_code": 200},
                    "request": {
                        "url": "https://hooks.slack.com/services/xxx/yyy",
                        "method": "POST",
                        "body": {"text": "summary"},
                    },
                    "response": {
                        "status_code": 200,
                        "body": "ok",
                    },
                },
                {
                    "channel_id": 2,
                    "channel_name": "DingTalk Backup",
                    "channel": "dingtalk",
                    "success": False,
                    "message": "DingTalk failed: invalid token",
                    "response_time": 0.12,
                    "details": {"status_code": 403},
                    "request": {
                        "url": "https://oapi.dingtalk.com/robot/send",
                        "method": "POST",
                        "body": {"msgtype": "markdown"},
                    },
                    "response": {
                        "status_code": 403,
                        "body": {"errmsg": "invalid token"},
                    },
                },
            ],
        }

    monkeypatch.setattr("app.queue.tasks.GitLabService.get_merge_request_changes", fake_get_changes)
    monkeypatch.setattr("app.queue.tasks.ReviewService.review_merge_request", fake_review_merge_request)
    monkeypatch.setattr("app.queue.tasks.NotificationDispatcher.dispatch", fake_dispatch)

    payload = {
        "object_kind": "merge_request",
        "project": {"id": project.project_id},
        "user": {"name": "Bob", "email": "bob@example.com"},
        "object_attributes": {
            "iid": 23,
            "title": "feat: add filter logs",
            "description": "desc",
            "source_branch": "feature/filter",
            "target_branch": "main",
            "url": "https://gitlab.example.com/group/trace-demo/-/merge_requests/23",
        },
    }
    result = await review_merge_request(
        {
            "payload": payload,
            "project_id": project.project_id,
            "webhook_log_id": webhook_log.id,
            "request_id": "req-3001",
            "event_type": "Merge Request Hook",
        }
    )
    assert result["status"] == "completed"

    async with get_session_factory()() as verify_db:
        refreshed = await verify_db.get(WebhookLog, webhook_log.id)
    assert refreshed is not None

    steps = (refreshed.pipeline_trace or {}).get("steps", [])
    filter_step = next((step for step in steps if step.get("name") == "changes_filtered"), None)
    assert filter_step is not None
    data = filter_step.get("data") or {}
    assert data.get("raw_file_count") == 3
    assert data.get("filtered_file_count") == 2
    assert data.get("removed_file_count") == 1
    assert data.get("ignored_by_pattern_count") == 1

    req_step = next((step for step in steps if step.get("name") == "llm_request_payload"), None)
    assert req_step is not None
    req_data = req_step.get("data") or {}
    assert req_data.get("protocol") == "openai_compatible"
    assert req_data.get("prompt_length") == 1024

    resp_step = next((step for step in steps if step.get("name") == "llm_response_payload"), None)
    assert resp_step is not None
    resp_data = resp_step.get("data") or {}
    assert resp_data.get("model") == "gpt-5-2025-08-07"
    assert resp_data.get("content_length") == 512

    summary_step = next((step for step in steps if step.get("name") == "notification_dispatched"), None)
    assert summary_step is not None
    summary_data = summary_step.get("data") or {}
    assert summary_data.get("channels") == 2
    assert summary_data.get("success_channels") == 1
    assert summary_data.get("failed_channels") == 1

    details_step = next((step for step in steps if step.get("name") == "notification_result_details"), None)
    assert details_step is not None
    details_data = details_step.get("data") or {}
    assert details_data.get("total_channels") == 2
    serialized = str(details_data.get("channels_detail") or "[]")
    parsed = json.loads(serialized)
    assert isinstance(parsed, list)
    assert len(parsed) == 2
    assert parsed[0].get("channel_name") == "Slack Main"
    assert parsed[1].get("channel_name") == "DingTalk Backup"

    slack_step = next((step for step in steps if step.get("name") == "notification_dispatch:Slack Main"), None)
    assert slack_step is not None
    slack_data = slack_step.get("data") or {}
    assert slack_data.get("channel") == "slack"
    assert slack_data.get("channel_name") == "Slack Main"
    assert slack_data.get("success") is True
    assert "hooks.slack.com" in str(slack_data.get("request") or "")
    assert "status_code" in str(slack_data.get("response") or "")

    dingtalk_step = next((step for step in steps if step.get("name") == "notification_dispatch:DingTalk Backup"), None)
    assert dingtalk_step is not None
    dingtalk_data = dingtalk_step.get("data") or {}
    assert dingtalk_data.get("channel") == "dingtalk"
    assert dingtalk_data.get("channel_name") == "DingTalk Backup"
    assert dingtalk_data.get("success") is False
    assert "oapi.dingtalk.com" in str(dingtalk_data.get("request") or "")
    assert "invalid token" in str(dingtalk_data.get("response") or "")


@pytest.mark.asyncio
async def test_review_pipeline_trace_fallbacks_gitlab_request_payload_when_missing(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = LLMProvider(
        name="mock-provider",
        protocol="mock",
        is_active=True,
        is_default=True,
        config_data={"model": "mock-model"},
    )
    db_session.add(provider)
    await db_session.flush()

    event_rule = WebhookEventRule(
        name="MR Rule",
        event_type="Merge Request Hook",
        description="",
        match_rules={"object_kind": "merge_request"},
        is_active=True,
    )
    db_session.add(event_rule)
    await db_session.flush()

    project = Project(
        project_id=3011,
        project_name="trace-gitlab-fallback-demo",
        project_path="group/trace-gitlab-fallback-demo",
        project_url="https://gitlab.example.com/group/trace-gitlab-fallback-demo.git",
        namespace="group",
        review_enabled=True,
        enabled_webhook_events=[event_rule.id],
        default_llm_provider_id=provider.id,
        gitlab_comment_notifications_enabled=True,
    )
    db_session.add(project)
    await db_session.flush()

    webhook_log = WebhookLog(
        event_type="Merge Request Hook",
        project_id=project.project_id,
        project_name=project.project_name,
        merge_request_iid=33,
        user_name="Eve",
        user_email="eve@example.com",
        source_branch="feature/gitlab-fallback",
        target_branch="main",
        payload={},
        request_headers={},
        request_body_raw="{}",
        request_id="req-3011",
    )
    db_session.add(webhook_log)
    await db_session.commit()

    async def fake_get_changes(self, project_id: int, mr_iid: int):  # noqa: ANN001
        _ = self, project_id, mr_iid
        return {"changes": [{"new_path": "src/A.java", "diff": "+a"}]}

    async def fake_review_merge_request(self, changes, payload, db):  # noqa: ANN001
        _ = self, changes, payload, db
        return {
            "content": "ok",
            "score": 90,
            "summary": "ok",
            "issues": [],
            "highlights": ["h1"],
            "files_reviewed": ["src/A.java"],
            "llm_model": "mock-model",
            "filter_summary": {"raw_file_count": 1, "filtered_file_count": 1, "removed_file_count": 0},
        }

    async def fake_dispatch(self, report_data, mr_info, project_id, db):  # noqa: ANN001
        _ = self, report_data, mr_info, project_id, db
        return {
            "success": True,
            "total_channels": 1,
            "success_channels": 1,
            "failed_channels": 0,
            "results": [
                {
                    "channel_id": None,
                    "channel_name": "GitLab Comment",
                    "channel": "gitlab",
                    "success": True,
                    "message": "GitLab comment sent",
                    "response_time": 0.21,
                    "details": {"note_id": 56118},
                    "request": None,
                    "response": {"note_id": 56118},
                }
            ],
        }

    monkeypatch.setattr("app.queue.tasks.GitLabService.get_merge_request_changes", fake_get_changes)
    monkeypatch.setattr("app.queue.tasks.ReviewService.review_merge_request", fake_review_merge_request)
    monkeypatch.setattr("app.queue.tasks.NotificationDispatcher.dispatch", fake_dispatch)

    payload = {
        "object_kind": "merge_request",
        "project": {"id": project.project_id},
        "user": {"name": "Eve", "email": "eve@example.com"},
        "object_attributes": {
            "iid": 33,
            "title": "feat: fallback request payload",
            "description": "desc",
            "source_branch": "feature/gitlab-fallback",
            "target_branch": "main",
            "url": "https://gitlab.example.com/group/trace-gitlab-fallback-demo/-/merge_requests/33",
        },
    }
    result = await review_merge_request(
        {
            "payload": payload,
            "project_id": project.project_id,
            "webhook_log_id": webhook_log.id,
            "request_id": "req-3011",
            "event_type": "Merge Request Hook",
        }
    )
    assert result["status"] == "completed"

    async with get_session_factory()() as verify_db:
        refreshed = await verify_db.get(WebhookLog, webhook_log.id)
    assert refreshed is not None

    steps = (refreshed.pipeline_trace or {}).get("steps", [])
    gitlab_step = next((step for step in steps if step.get("name") == "notification_dispatch:GitLab Comment"), None)
    assert gitlab_step is not None
    gitlab_data = gitlab_step.get("data") or {}
    request_text = str(gitlab_data.get("request") or "")
    assert "queue_generated_request" in request_text
    assert "\"project_id\": 3011" in request_text
    assert "\"mr_iid\": 33" in request_text
