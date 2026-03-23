from __future__ import annotations

import pytest

from app.services.notification import NotificationDispatcher


@pytest.mark.asyncio
async def test_send_to_gitlab_records_full_request_and_response_payloads(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_post_merge_request_comment(self, project_id: int, mr_iid: int, comment: str):  # noqa: ANN001
        _ = self
        assert project_id == 47
        assert mr_iid == 17758
        assert "AI 代码审查结果" in comment
        return {
            "id": 56169,
            "body": comment,
            "type": "DiffNote",
            "system": False,
        }

    monkeypatch.setattr(
        "app.services.notification.GitLabService.post_merge_request_comment",
        fake_post_merge_request_comment,
    )

    dispatcher = NotificationDispatcher(request_id="req-gitlab-trace")
    result = await dispatcher._send_to_gitlab(
        report_data={"content": "review content"},
        mr_info={
            "project_id": 47,
            "mr_iid": 17758,
            "project_name": "demo",
            "title": "feat: enrich gitlab trace",
        },
        db=db_session,
    )

    assert result.get("success") is True
    details = result.get("details") or {}
    request_payload = details.get("request")
    assert isinstance(request_payload, dict)
    assert request_payload.get("project_id") == 47
    assert request_payload.get("mr_iid") == 17758
    assert request_payload.get("method") == "POST"
    assert request_payload.get("endpoint") == "/api/v4/projects/47/merge_requests/17758/notes"
    body = request_payload.get("body")
    assert isinstance(body, dict)
    assert "AI 代码审查结果" in str(body.get("body") or "")
    assert request_payload.get("comment_length") == len(str(body.get("body") or ""))

    response_payload = details.get("response")
    assert isinstance(response_payload, dict)
    assert response_payload.get("note_id") == 56169
    response_body = response_payload.get("body")
    assert isinstance(response_body, dict)
    assert response_body.get("id") == 56169
    assert "body" in response_body
