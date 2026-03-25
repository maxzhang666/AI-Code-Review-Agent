from __future__ import annotations

import pytest
from sqlalchemy import select

from app.database import get_session_factory
from app.models import MRFeedbackRecord, Project, WebhookEventRule, WebhookLog
from app.queue.tasks import review_merge_request


@pytest.mark.asyncio
async def test_note_hook_ignore_command_by_maintainer_posts_confirmation(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_rule = WebhookEventRule(
        name="MR Feedback Command",
        event_type="Note Hook",
        description="",
        match_rules={"object_kind": "note", "object_attributes": {"noteable_type": "MergeRequest"}},
        is_active=True,
    )
    db_session.add(event_rule)
    await db_session.flush()

    project = Project(
        project_id=4101,
        project_name="feedback-demo",
        project_path="group/feedback-demo",
        project_url="https://gitlab.example.com/group/feedback-demo.git",
        namespace="group",
        review_enabled=True,
        enabled_webhook_events=[event_rule.id],
    )
    db_session.add(project)
    await db_session.flush()

    webhook_log = WebhookLog(
        event_type="Note Hook",
        project_id=project.project_id,
        project_name=project.project_name,
        merge_request_iid=12,
        user_name="Lead",
        user_email="lead@example.com",
        source_branch="",
        target_branch="",
        payload={},
        request_headers={},
        request_body_raw="{}",
        request_id="req-note-1",
    )
    db_session.add(webhook_log)
    await db_session.commit()

    comments: list[str] = []

    async def fake_get_member_access_level(self, project_id: int, user_id: int):  # noqa: ANN001
        _ = self, project_id, user_id
        return 40

    async def fake_post_comment(self, project_id: int, mr_iid: int, comment: str):  # noqa: ANN001
        _ = self, project_id, mr_iid
        comments.append(comment)
        return {"id": 9001}

    monkeypatch.setattr(
        "app.queue.tasks.GitLabService.get_project_member_access_level",
        fake_get_member_access_level,
    )
    monkeypatch.setattr(
        "app.queue.tasks.GitLabService.post_merge_request_comment",
        fake_post_comment,
    )

    payload = {
        "object_kind": "note",
        "project": {"id": project.project_id},
        "user": {"id": 777, "name": "Lead", "email": "lead@example.com"},
        "object_attributes": {
            "noteable_type": "MergeRequest",
            "noteable_iid": 12,
            "note": "/cra ignore I-7 reason: 历史包袱，本次不处理",
        },
    }

    result = await review_merge_request(
        {
            "payload": payload,
            "project_id": project.project_id,
            "webhook_log_id": webhook_log.id,
            "request_id": "req-note-1",
            "event_type": "Note Hook",
        }
    )

    assert result["status"] == "completed"
    assert result["mode"] == "note_feedback"
    assert result["action"] == "ignore"
    assert result["issue_id"] == "I-7"
    assert isinstance(result.get("feedback_record_id"), int)
    assert any("已回收" in msg for msg in comments)

    async with get_session_factory()() as verify_db:
        refreshed = await verify_db.get(WebhookLog, webhook_log.id)
        row = (
            await verify_db.execute(
                select(MRFeedbackRecord).where(MRFeedbackRecord.project_id == project.project_id)
            )
        ).scalars().first()
    assert refreshed is not None
    assert refreshed.processed is True
    assert row is not None
    assert row.action == "ignore"
    assert row.issue_id == "I-7"
    assert "历史包袱" in row.reason


@pytest.mark.asyncio
async def test_note_hook_ignore_command_by_developer_is_rejected(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_rule = WebhookEventRule(
        name="MR Feedback Command",
        event_type="Note Hook",
        description="",
        match_rules={"object_kind": "note", "object_attributes": {"noteable_type": "MergeRequest"}},
        is_active=True,
    )
    db_session.add(event_rule)
    await db_session.flush()

    project = Project(
        project_id=4102,
        project_name="feedback-demo-2",
        project_path="group/feedback-demo-2",
        project_url="https://gitlab.example.com/group/feedback-demo-2.git",
        namespace="group",
        review_enabled=True,
        enabled_webhook_events=[event_rule.id],
    )
    db_session.add(project)
    await db_session.flush()

    webhook_log = WebhookLog(
        event_type="Note Hook",
        project_id=project.project_id,
        project_name=project.project_name,
        merge_request_iid=9,
        user_name="Dev",
        user_email="dev@example.com",
        source_branch="",
        target_branch="",
        payload={},
        request_headers={},
        request_body_raw="{}",
        request_id="req-note-2",
    )
    db_session.add(webhook_log)
    await db_session.commit()

    comments: list[str] = []

    async def fake_get_member_access_level(self, project_id: int, user_id: int):  # noqa: ANN001
        _ = self, project_id, user_id
        return 30

    async def fake_post_comment(self, project_id: int, mr_iid: int, comment: str):  # noqa: ANN001
        _ = self, project_id, mr_iid
        comments.append(comment)
        return {"id": 9002}

    monkeypatch.setattr(
        "app.queue.tasks.GitLabService.get_project_member_access_level",
        fake_get_member_access_level,
    )
    monkeypatch.setattr(
        "app.queue.tasks.GitLabService.post_merge_request_comment",
        fake_post_comment,
    )

    payload = {
        "object_kind": "note",
        "project": {"id": project.project_id},
        "user": {"id": 778, "name": "Dev", "email": "dev@example.com"},
        "object_attributes": {
            "noteable_type": "MergeRequest",
            "noteable_iid": 9,
            "note": "/cra ignore I-2 reason: 看起来是误报",
        },
    }

    result = await review_merge_request(
        {
            "payload": payload,
            "project_id": project.project_id,
            "webhook_log_id": webhook_log.id,
            "request_id": "req-note-2",
            "event_type": "Note Hook",
        }
    )

    assert result["status"] == "skipped"
    assert result["reason"] == "insufficient_permission"
    assert any("Maintainer" in msg or "Owner" in msg for msg in comments)
