from __future__ import annotations

from datetime import datetime

import pytest

from app.models import MRFeedbackRecord, MergeRequestReview, ReviewFinding


@pytest.mark.asyncio
async def test_get_developer_weekly_report(client, db_session) -> None:
    review = MergeRequestReview(
        project_id=9901,
        project_name="dev-api",
        merge_request_iid=3,
        merge_request_title="MR-3",
        source_branch="feat/a",
        target_branch="main",
        author_name="dev",
        author_email="dev@example.com",
        created_at=datetime(2026, 3, 24, 9, 0, 0),
        status="completed",
        total_files=1,
    )
    db_session.add(review)
    await db_session.flush()

    db_session.add(
        ReviewFinding(
            review_id=review.id,
            fingerprint="api-dev-f-1",
            category="quality",
            severity="medium",
            owner_name="alice",
            owner_email="alice@example.com",
            created_at=datetime(2026, 3, 24, 9, 5, 0),
        )
    )
    await db_session.commit()

    response = await client.get(
        "/api/webhook/reports/developers/weekly/?owner=alice&anchor_date=2026-03-25"
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["week_start"] == "2026-03-23"
    assert payload["week_end"] == "2026-03-29"
    assert payload["owner"] == "alice"
    assert payload["summary"]["total_findings"] == 1
    assert payload["summary"]["total_reviews"] == 1
    assert payload["ai_summary"]


@pytest.mark.asyncio
async def test_get_developer_weekly_report_include_statuses_query(client, db_session) -> None:
    review = MergeRequestReview(
        project_id=9902,
        project_name="dev-api-status",
        merge_request_iid=13,
        merge_request_title="MR-13",
        source_branch="feat/status",
        target_branch="main",
        author_name="dev",
        author_email="dev@example.com",
        created_at=datetime(2026, 3, 24, 9, 0, 0),
        status="completed",
        total_files=1,
    )
    db_session.add(review)
    await db_session.flush()

    db_session.add_all(
        [
            ReviewFinding(
                review_id=review.id,
                issue_id="I-1",
                fingerprint="api-dev-status-f-1",
                category="quality",
                severity="medium",
                owner_name="alice",
                owner_email="alice@example.com",
                created_at=datetime(2026, 3, 24, 9, 5, 0),
            ),
            ReviewFinding(
                review_id=review.id,
                issue_id="I-2",
                fingerprint="api-dev-status-f-2",
                category="style",
                severity="low",
                owner_name="alice",
                owner_email="alice@example.com",
                created_at=datetime(2026, 3, 24, 9, 6, 0),
            ),
        ]
    )
    db_session.add(
        MRFeedbackRecord(
            project_id=9902,
            merge_request_iid=13,
            review_id=review.id,
            issue_id="I-1",
            rule_key="quality.null-check",
            action="ignore",
            reason="历史包袱",
            operator_gitlab_id=3001,
            operator_name="Lead",
            operator_role="maintainer",
            source_note_id=5001,
            source_note_body="/cra ignore I-1 reason: 历史包袱",
            created_at=datetime(2026, 3, 24, 11, 0, 0),
        )
    )
    await db_session.commit()

    response_default = await client.get(
        "/api/webhook/reports/developers/weekly/?owner=alice&anchor_date=2026-03-25"
    )
    assert response_default.status_code == 200
    payload_default = response_default.json()
    assert payload_default["include_statuses"] == ["open", "reopened"]
    assert payload_default["summary"]["raw_total_findings"] == 2
    assert payload_default["summary"]["total_findings"] == 1

    response_include_ignored = await client.get(
        "/api/webhook/reports/developers/weekly/?owner=alice&anchor_date=2026-03-25"
        "&include_statuses=open&include_statuses=ignored&include_statuses=reopened"
    )
    assert response_include_ignored.status_code == 200
    payload_include_ignored = response_include_ignored.json()
    assert payload_include_ignored["include_statuses"] == ["open", "ignored", "reopened"]
    assert payload_include_ignored["summary"]["total_findings"] == 2
