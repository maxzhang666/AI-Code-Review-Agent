from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_initialize_default_webhook_rules_includes_note_hook(client) -> None:
    response = await client.post("/api/webhook-event-rules/initialize_defaults/")
    assert response.status_code == 200

    list_response = await client.get("/api/webhook-event-rules/")
    assert list_response.status_code == 200
    data = list_response.json()
    rules = data.get("results", [])

    feedback_rule = next(
        (
            item
            for item in rules
            if item.get("event_type") == "Note Hook" and item.get("name") == "MR Feedback Command"
        ),
        None,
    )
    assert feedback_rule is not None
    assert feedback_rule.get("match_rules") == {
        "object_kind": "note",
        "object_attributes": {"noteable_type": "MergeRequest"},
    }

