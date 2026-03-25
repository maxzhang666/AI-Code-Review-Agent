from __future__ import annotations

from datetime import datetime

import pytest

from app.models import MRFeedbackRecord, Project


@pytest.mark.asyncio
async def test_get_mr_feedback_weekly_report(client, db_session) -> None:
    project = Project(
        project_id=8801,
        project_name="report-demo",
        project_path="group/report-demo",
        project_url="https://gitlab.example.com/group/report-demo.git",
        namespace="group",
        review_enabled=True,
    )
    db_session.add(project)
    await db_session.flush()

    db_session.add(
        MRFeedbackRecord(
            project_id=8801,
            merge_request_iid=31,
            review_id=None,
            issue_id="I-3",
            rule_key="style.naming",
            action="ignore",
            reason="历史包袱，本周不改",
            operator_gitlab_id=7001,
            operator_name="Lead",
            operator_role="maintainer",
            source_note_id=12001,
            source_note_body="/cra ignore I-3 reason: 历史包袱",
            created_at=datetime(2026, 3, 24, 9, 0, 0),
        )
    )
    await db_session.commit()

    response = await client.get("/api/webhook/reports/mr-feedback/weekly/?anchor_date=2026-03-25")
    assert response.status_code == 200

    payload = response.json()
    assert payload["week_start"] == "2026-03-23"
    assert payload["week_end"] == "2026-03-29"
    assert payload["summary"]["ignored_count"] == 1
    assert payload["summary"]["reopened_count"] == 0
    assert payload["summary"]["feedback_actions"] == 1
    assert payload["projects"][0]["project_id"] == 8801
    assert payload["suggested_policy_changes"]

