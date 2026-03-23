from __future__ import annotations

import pytest

from app.models import NotificationChannel
from app.services.notification import NotificationDispatcher


@pytest.mark.asyncio
async def test_dispatch_exposes_normalized_trace_error_meta_fields(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    channel = NotificationChannel(
        name="Slack Main",
        notification_type="slack",
        description="",
        is_active=True,
        is_default=True,
        config_data={"webhook_url": "https://hooks.slack.example/services/test"},
    )
    db_session.add(channel)
    await db_session.commit()

    async def fake_send_to_channel(self, channel, report_data, mr_info, db):  # noqa: ANN001
        _ = self, channel, report_data, mr_info, db
        return {
            "success": False,
            "message": "Slack failed: HTTP 500",
            "response_time": 0.21,
            "details": {
                "status_code": 500,
                "request": {"url": "https://hooks.slack.example/services/test", "method": "POST"},
                "response": {"status_code": 500, "body": "internal error"},
            },
        }

    monkeypatch.setattr("app.services.notification.NotificationDispatcher._send_to_channel", fake_send_to_channel)

    dispatcher = NotificationDispatcher(request_id="req-normalized")
    result = await dispatcher.dispatch(
        report_data={"content": "review content"},
        mr_info={"project_id": 5002, "mr_iid": 89, "title": "demo"},
        project_id=5002,
        db=db_session,
    )

    entries = result.get("results") or []
    assert len(entries) == 1
    first = entries[0]
    assert first.get("channel") == "slack"
    assert first.get("success") is False

    trace = first.get("trace")
    assert isinstance(trace, dict)
    assert trace.get("request", {}).get("method") == "POST"
    assert trace.get("response", {}).get("status_code") == 500

    error = first.get("error")
    assert isinstance(error, dict)
    assert error.get("code") == "channel_send_failed"
    assert "HTTP 500" in str(error.get("message") or "")

    meta = first.get("meta")
    assert isinstance(meta, dict)
    assert meta.get("status_code") == 500
