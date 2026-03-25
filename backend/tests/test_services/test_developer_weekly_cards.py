from __future__ import annotations

from datetime import date, datetime

import pytest

from app.models import MRFeedbackRecord, MergeRequestReview, ReviewFinding
from app.services.reporting import generate_developer_weekly_cards


@pytest.mark.asyncio
async def test_generate_developer_weekly_cards_returns_member_cards(db_session) -> None:
    review = MergeRequestReview(
        project_id=8801,
        project_name="cards-demo",
        merge_request_iid=21,
        merge_request_title="MR-21",
        source_branch="feat/cards",
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
                fingerprint="card-a-1",
                category="quality",
                severity="high",
                owner_name="alice",
                owner_email="alice@example.com",
                created_at=datetime(2026, 3, 24, 9, 10, 0),
            ),
            ReviewFinding(
                review_id=review.id,
                fingerprint="card-a-2",
                category="quality",
                severity="medium",
                owner_name="alice",
                owner_email="alice@example.com",
                created_at=datetime(2026, 3, 24, 9, 11, 0),
            ),
            ReviewFinding(
                review_id=review.id,
                fingerprint="card-b-1",
                category="style",
                severity="low",
                owner_name="bob",
                owner_email="bob@example.com",
                created_at=datetime(2026, 3, 24, 9, 12, 0),
            ),
        ]
    )
    db_session.add(
        MRFeedbackRecord(
            project_id=8801,
            merge_request_iid=21,
            review_id=review.id,
            issue_id="I-1",
            rule_key="quality.null-check",
            action="ignore",
            reason="历史包袱",
            operator_gitlab_id=7001,
            operator_name="Lead",
            operator_role="maintainer",
            source_note_id=9001,
            source_note_body="/cra ignore I-1 reason: 历史包袱",
            created_at=datetime(2026, 3, 24, 10, 0, 0),
        )
    )
    await db_session.commit()

    result = await generate_developer_weekly_cards(
        db_session,
        anchor_date=date(2026, 3, 25),
        limit=10,
    )

    assert result["week_start"] == "2026-03-23"
    assert result["week_end"] == "2026-03-29"
    assert result["count"] == 2
    assert result["results"][0]["owner"] == "alice"
    assert result["results"][0]["total_findings"] == 2
    assert result["results"][0]["top_category"] == "quality"
    assert result["results"][0]["summary_excerpt"]
    assert result["results"][0]["improvement_focus"]


@pytest.mark.asyncio
async def test_generate_developer_weekly_cards_excludes_ignored_findings_by_default(db_session) -> None:
    review = MergeRequestReview(
        project_id=8802,
        project_name="cards-status",
        merge_request_iid=31,
        merge_request_title="MR-31",
        source_branch="feat/cards-status",
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
                fingerprint="card-status-a-1",
                category="quality",
                severity="high",
                owner_name="alice",
                owner_email="alice@example.com",
                created_at=datetime(2026, 3, 24, 9, 10, 0),
            ),
            ReviewFinding(
                review_id=review.id,
                issue_id="I-2",
                fingerprint="card-status-a-2",
                category="style",
                severity="medium",
                owner_name="alice",
                owner_email="alice@example.com",
                created_at=datetime(2026, 3, 24, 9, 11, 0),
            ),
        ]
    )
    db_session.add(
        MRFeedbackRecord(
            project_id=8802,
            merge_request_iid=31,
            review_id=review.id,
            issue_id="I-1",
            rule_key="quality.null-check",
            action="ignore",
            reason="历史包袱",
            operator_gitlab_id=7001,
            operator_name="Lead",
            operator_role="maintainer",
            source_note_id=9001,
            source_note_body="/cra ignore I-1 reason: 历史包袱",
            created_at=datetime(2026, 3, 24, 10, 0, 0),
        )
    )
    await db_session.commit()

    default_cards = await generate_developer_weekly_cards(
        db_session,
        anchor_date=date(2026, 3, 25),
        limit=10,
    )
    assert default_cards["include_statuses"] == ["open", "reopened"]
    assert default_cards["count"] == 1
    assert default_cards["results"][0]["owner"] == "alice"
    assert default_cards["results"][0]["raw_total_findings"] == 2
    assert default_cards["results"][0]["total_findings"] == 1

    include_ignored_cards = await generate_developer_weekly_cards(
        db_session,
        anchor_date=date(2026, 3, 25),
        limit=10,
        include_statuses=["open", "reopened", "ignored"],
    )
    assert include_ignored_cards["include_statuses"] == ["open", "ignored", "reopened"]
    assert include_ignored_cards["results"][0]["total_findings"] == 2
