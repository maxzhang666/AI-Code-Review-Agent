from __future__ import annotations

from datetime import date, datetime

import pytest
from sqlalchemy import select

from app.models import DeveloperWeeklySummary, MRFeedbackRecord, MergeRequestReview, ReviewFinding
from app.services.reporting.developer_weekly_snapshot import generate_last_week_developer_weekly_summaries


@pytest.mark.asyncio
async def test_reports_api_prefers_cached_developer_weekly_summary(client, db_session) -> None:
    review = MergeRequestReview(
        project_id=9801,
        project_name="snapshot-api",
        merge_request_iid=21,
        merge_request_title="MR-21",
        source_branch="feat/snapshot-api",
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
                fingerprint="snapshot-api-f-1",
                category="quality",
                severity="high",
                owner_name="alice",
                owner_email="alice@example.com",
                created_at=datetime(2026, 3, 24, 9, 10, 0),
            ),
            ReviewFinding(
                review_id=review.id,
                issue_id="I-2",
                fingerprint="snapshot-api-f-2",
                category="style",
                severity="low",
                owner_name="alice",
                owner_email="alice@example.com",
                created_at=datetime(2026, 3, 24, 9, 11, 0),
            ),
        ]
    )
    db_session.add(
        MRFeedbackRecord(
            project_id=9801,
            merge_request_iid=21,
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

    await generate_last_week_developer_weekly_summaries(
        db_session,
        reference_date=date(2026, 3, 30),
        use_llm=False,
    )

    snapshot = (
        await db_session.execute(
            select(DeveloperWeeklySummary).where(
                DeveloperWeeklySummary.week_start == date(2026, 3, 23),
                DeveloperWeeklySummary.owner_name == "alice",
            )
        )
    ).scalars().first()
    assert snapshot is not None
    snapshot.ai_summary = "CACHED_SUMMARY_MARKER"
    report_payload = dict(snapshot.report_payload or {})
    report_payload["ai_summary"] = "CACHED_SUMMARY_MARKER"
    snapshot.report_payload = report_payload
    card_payload = dict(snapshot.card_payload or {})
    card_payload["summary_excerpt"] = "CACHED_SUMMARY_MARKER"
    snapshot.card_payload = card_payload
    await db_session.commit()

    detail_response = await client.get(
        "/api/webhook/reports/developers/weekly/?owner=alice&anchor_date=2026-03-25"
    )
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["ai_summary"] == "CACHED_SUMMARY_MARKER"
    assert detail_payload["source"] == "heuristic"

    cards_response = await client.get(
        "/api/webhook/reports/developers/weekly/cards/?anchor_date=2026-03-25&limit=10"
    )
    assert cards_response.status_code == 200
    cards_payload = cards_response.json()
    assert cards_payload["results"][0]["summary_excerpt"] == "CACHED_SUMMARY_MARKER"
