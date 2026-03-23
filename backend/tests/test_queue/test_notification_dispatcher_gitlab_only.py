from __future__ import annotations

import pytest

from app.models import Project
from app.services.notification import NotificationDispatcher


@pytest.mark.asyncio
async def test_dispatch_uses_gitlab_comment_when_enabled_without_channels(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = Project(
        project_id=5001,
        project_name="gitlab-only-demo",
        project_path="group/gitlab-only-demo",
        project_url="https://gitlab.example.com/group/gitlab-only-demo.git",
        namespace="group",
        review_enabled=True,
        gitlab_comment_notifications_enabled=True,
    )
    db_session.add(project)
    await db_session.commit()

    async def fake_send_to_gitlab(self, report_data, mr_info, db):  # noqa: ANN001
        _ = self, report_data, mr_info, db
        return {
            "success": True,
            "message": "GitLab comment sent",
            "response_time": 0.11,
            "details": {"note_id": 9527},
        }

    monkeypatch.setattr("app.services.notification.NotificationDispatcher._send_to_gitlab", fake_send_to_gitlab)

    dispatcher = NotificationDispatcher(request_id="req-gitlab-only")
    result = await dispatcher.dispatch(
        report_data={"content": "review content"},
        mr_info={"project_id": project.project_id, "mr_iid": 88, "title": "demo"},
        project_id=project.project_id,
        db=db_session,
    )

    assert result.get("total_channels") == 1
    assert result.get("success_channels") == 1
    assert result.get("failed_channels") == 0
    entries = result.get("results") or []
    assert len(entries) == 1
    assert entries[0].get("channel") == "gitlab"
    assert entries[0].get("channel_name") == "GitLab Comment"
    assert entries[0].get("success") is True
    request_payload = entries[0].get("request")
    assert isinstance(request_payload, dict)
    assert request_payload.get("project_id") == 5001
    assert request_payload.get("mr_iid") == 88
    assert request_payload.get("method") == "POST"
    assert request_payload.get("fallback") == "dispatcher_generated_request"
    body = request_payload.get("body")
    assert isinstance(body, dict)
    assert "AI 代码审查结果" in str(body.get("body") or "")

    response_payload = entries[0].get("response")
    assert isinstance(response_payload, dict)
    assert response_payload.get("note_id") == 9527
