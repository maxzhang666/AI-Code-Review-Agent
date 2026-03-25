from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.models import MRFeedbackRecord


@pytest.mark.asyncio
async def test_list_mr_feedback_records_supports_project_and_action_filters(
    client,
    db_session,
) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    db_session.add_all(
        [
            MRFeedbackRecord(
                project_id=5001,
                merge_request_iid=11,
                review_id=None,
                issue_id="I-1",
                rule_key="reliability.null-check",
                action="ignore",
                reason="历史包袱",
                operator_gitlab_id=101,
                operator_name="Lead A",
                operator_role="maintainer",
                source_note_id=9001,
                source_note_body="/cra ignore I-1 reason: 历史包袱",
                created_at=now - timedelta(days=1),
            ),
            MRFeedbackRecord(
                project_id=5002,
                merge_request_iid=15,
                review_id=None,
                issue_id="I-9",
                rule_key="style.naming",
                action="reopen",
                reason="已进入重构范围",
                operator_gitlab_id=102,
                operator_name="Lead B",
                operator_role="maintainer",
                source_note_id=9002,
                source_note_body="/cra reopen I-9 reason: 已进入重构范围",
                created_at=now - timedelta(days=2),
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/webhook/mr-feedback/records/?project_id=5001&action=ignore")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert len(payload["results"]) == 1
    assert payload["results"][0]["project_id"] == 5001
    assert payload["results"][0]["action"] == "ignore"
    assert payload["results"][0]["issue_id"] == "I-1"


@pytest.mark.asyncio
async def test_list_mr_feedback_records_supports_time_window(client, db_session) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    db_session.add_all(
        [
            MRFeedbackRecord(
                project_id=5101,
                merge_request_iid=21,
                review_id=None,
                issue_id="I-3",
                rule_key="security.auth",
                action="ignore",
                reason="业务特例",
                operator_gitlab_id=103,
                operator_name="Lead C",
                operator_role="owner",
                source_note_id=9101,
                source_note_body="/cra ignore I-3 reason: 业务特例",
                created_at=now - timedelta(days=1),
            ),
            MRFeedbackRecord(
                project_id=5101,
                merge_request_iid=22,
                review_id=None,
                issue_id="I-4",
                rule_key="security.auth",
                action="ignore",
                reason="历史包袱",
                operator_gitlab_id=103,
                operator_name="Lead C",
                operator_role="owner",
                source_note_id=9102,
                source_note_body="/cra ignore I-4 reason: 历史包袱",
                created_at=now - timedelta(days=14),
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/webhook/mr-feedback/records/?project_id=5101&days=7")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["issue_id"] == "I-3"

