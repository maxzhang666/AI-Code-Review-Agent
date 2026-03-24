from __future__ import annotations

from datetime import datetime as real_datetime

import pytest
from app.database import get_session_factory
from app.models import LLMProvider, MergeRequestReview, Project, WebhookEventRule, WebhookLog
from app.queue.tasks import review_merge_request


@pytest.mark.asyncio
async def test_review_pipeline_trace_contains_enriched_steps(db_session) -> None:
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
        project_id=1001,
        project_name="demo-project",
        project_path="group/demo-project",
        project_url="https://gitlab.example.com/group/demo-project.git",
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
        merge_request_iid=12,
        user_name="Alice",
        user_email="alice@example.com",
        source_branch="feature/logging",
        target_branch="main",
        payload={},
        request_headers={},
        request_body_raw="{}",
        request_id="req-123",
    )
    db_session.add(webhook_log)
    await db_session.commit()

    payload = {
        "object_kind": "merge_request",
        "project": {"id": project.project_id},
        "user": {"name": "Alice", "email": "alice@example.com"},
        "object_attributes": {
            "iid": 12,
            "title": "feat: improve tracing",
            "description": "test description",
            "source_branch": "feature/logging",
            "target_branch": "main",
            "url": "https://gitlab.example.com/group/demo-project/-/merge_requests/12",
        },
    }
    result = await review_merge_request(
        {
            "payload": payload,
            "project_id": project.project_id,
            "webhook_log_id": webhook_log.id,
            "request_id": "req-123",
            "event_type": "Merge Request Hook",
        }
    )
    assert result["status"] == "completed"

    async with get_session_factory()() as verify_db:
        refreshed = await verify_db.get(WebhookLog, webhook_log.id)
    assert refreshed is not None

    pipeline_trace = refreshed.pipeline_trace or {}
    steps = pipeline_trace.get("steps", [])
    step_names = [step.get("name") for step in steps]
    assert "event_rule_matched" in step_names
    assert "mr_context_parsed" in step_names
    assert "review_record_created" in step_names
    assert "review_result_ready" in step_names
    assert "report_generated" in step_names
    assert any(str(name).startswith("notification_dispatch:") for name in step_names)
    assert "notification_dispatched" in step_names
    assert "notification_result_details" in step_names
    notification_step = next(
        (step for step in steps if str(step.get("name")).startswith("notification_dispatch:")),
        None,
    )
    assert notification_step is not None
    notification_data = notification_step.get("data") or {}
    assert "request" in notification_data
    assert "response" in notification_data
    assert "comment_length" in str(notification_data.get("request") or "")

    event_rule_step = next(step for step in steps if step.get("name") == "event_rule_matched")
    event_data = event_rule_step.get("data") or {}
    assert event_data.get("rule_id") == event_rule.id
    assert event_data.get("rule_name") == "MR Rule"

    mr_step = next(step for step in steps if step.get("name") == "mr_context_parsed")
    mr_data = mr_step.get("data") or {}
    assert mr_data.get("mr_iid") == 12
    assert mr_data.get("source_branch") == "feature/logging"
    assert mr_data.get("target_branch") == "main"


@pytest.mark.asyncio
async def test_review_pipeline_persists_completed_and_processed_time_in_utc(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.queue import tasks as tasks_module

    utc_stamp = real_datetime(2026, 2, 1, 1, 2, 3)
    local_stamp = real_datetime(2026, 2, 1, 9, 2, 3)

    class FakeDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ARG003
            return utc_stamp if tz is not None else local_stamp

        @classmethod
        def utcnow(cls):
            return utc_stamp

    monkeypatch.setattr(tasks_module, "datetime", FakeDateTime)

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
        project_id=1002,
        project_name="demo-project-utc",
        project_path="group/demo-project-utc",
        project_url="https://gitlab.example.com/group/demo-project-utc.git",
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
        merge_request_iid=34,
        user_name="Alice",
        user_email="alice@example.com",
        source_branch="feature/utc-time",
        target_branch="main",
        payload={},
        request_headers={},
        request_body_raw="{}",
        request_id="req-utc-1",
    )
    db_session.add(webhook_log)
    await db_session.commit()

    payload = {
        "object_kind": "merge_request",
        "project": {"id": project.project_id},
        "user": {"name": "Alice", "email": "alice@example.com"},
        "object_attributes": {
            "iid": 34,
            "title": "fix: normalize timestamp",
            "description": "test description",
            "source_branch": "feature/utc-time",
            "target_branch": "main",
            "url": "https://gitlab.example.com/group/demo-project-utc/-/merge_requests/34",
        },
    }
    result = await review_merge_request(
        {
            "payload": payload,
            "project_id": project.project_id,
            "webhook_log_id": webhook_log.id,
            "request_id": "req-utc-1",
            "event_type": "Merge Request Hook",
        }
    )
    assert result["status"] == "completed"

    async with get_session_factory()() as verify_db:
        review = await verify_db.get(MergeRequestReview, result["review_id"])
        refreshed_webhook = await verify_db.get(WebhookLog, webhook_log.id)

    assert review is not None
    assert refreshed_webhook is not None
    assert review.completed_at == utc_stamp
    assert refreshed_webhook.processed_at == utc_stamp
