from __future__ import annotations

from datetime import datetime

import pytest

from app.models import MRFeedbackRecord, MergeRequestReview, ReviewFinding


@pytest.mark.asyncio
async def test_get_developer_weekly_cards(client, db_session) -> None:
    review = MergeRequestReview(
        project_id=9101,
        project_name="cards-api",
        merge_request_iid=6,
        merge_request_title="MR-6",
        source_branch="feat/api",
        target_branch="main",
        author_name="dev",
        author_email="dev@example.com",
        created_at=datetime(2026, 3, 24, 9, 0, 0),
        status="completed",
    )
    db_session.add(review)
    await db_session.flush()
    db_session.add(
        ReviewFinding(
            review_id=review.id,
            fingerprint="api-card-1",
            category="security",
            severity="high",
            owner_name="carol",
            owner_email="carol@example.com",
            created_at=datetime(2026, 3, 24, 9, 10, 0),
        )
    )
    await db_session.commit()

    response = await client.get(
        "/api/webhook/reports/developers/weekly/cards/?anchor_date=2026-03-25&limit=10"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["week_start"] == "2026-03-23"
    assert payload["count"] == 1
    assert payload["results"][0]["owner"] == "carol"
    assert payload["results"][0]["top_category"] == "security"


@pytest.mark.asyncio
async def test_get_developer_weekly_cards_include_statuses_query(client, db_session) -> None:
    review = MergeRequestReview(
        project_id=9102,
        project_name="cards-api-status",
        merge_request_iid=16,
        merge_request_title="MR-16",
        source_branch="feat/api-status",
        target_branch="main",
        author_name="dev",
        author_email="dev@example.com",
        created_at=datetime(2026, 3, 24, 9, 0, 0),
        status="completed",
    )
    db_session.add(review)
    await db_session.flush()
    db_session.add_all(
        [
            ReviewFinding(
                review_id=review.id,
                issue_id="I-1",
                fingerprint="api-card-status-1",
                category="security",
                severity="high",
                owner_name="carol",
                owner_email="carol@example.com",
                created_at=datetime(2026, 3, 24, 9, 10, 0),
            ),
            ReviewFinding(
                review_id=review.id,
                issue_id="I-2",
                fingerprint="api-card-status-2",
                category="style",
                severity="low",
                owner_name="carol",
                owner_email="carol@example.com",
                created_at=datetime(2026, 3, 24, 9, 11, 0),
            ),
        ]
    )
    db_session.add(
        MRFeedbackRecord(
            project_id=9102,
            merge_request_iid=16,
            review_id=review.id,
            issue_id="I-1",
            rule_key="security.auth",
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
        "/api/webhook/reports/developers/weekly/cards/?anchor_date=2026-03-25&limit=10"
    )
    assert response_default.status_code == 200
    payload_default = response_default.json()
    assert payload_default["include_statuses"] == ["open", "reopened"]
    assert payload_default["results"][0]["raw_total_findings"] == 2
    assert payload_default["results"][0]["total_findings"] == 1

    response_include_ignored = await client.get(
        "/api/webhook/reports/developers/weekly/cards/?anchor_date=2026-03-25&limit=10"
        "&include_statuses=open&include_statuses=ignored&include_statuses=reopened"
    )
    assert response_include_ignored.status_code == 200
    payload_include_ignored = response_include_ignored.json()
    assert payload_include_ignored["include_statuses"] == ["open", "ignored", "reopened"]
    assert payload_include_ignored["results"][0]["total_findings"] == 2
