from __future__ import annotations

from datetime import date, datetime

import pytest

from app.models import MRFeedbackRecord, MergeRequestReview, ReviewFinding
from app.services.reporting.developer_weekly_snapshot import (
    generate_last_week_developer_weekly_summaries,
    get_cached_developer_weekly_cards,
    get_cached_developer_weekly_report,
)


@pytest.mark.asyncio
async def test_generate_last_week_developer_weekly_summaries_and_read_cache(db_session) -> None:
    review = MergeRequestReview(
        project_id=9701,
        project_name="snapshot-demo",
        merge_request_iid=11,
        merge_request_title="MR-11",
        source_branch="feat/snapshot",
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
                fingerprint="snapshot-f-1",
                category="quality",
                severity="high",
                owner_name="alice",
                owner_email="alice@example.com",
                created_at=datetime(2026, 3, 24, 9, 10, 0),
            ),
            ReviewFinding(
                review_id=review.id,
                issue_id="I-2",
                fingerprint="snapshot-f-2",
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
            project_id=9701,
            merge_request_iid=11,
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

    generation = await generate_last_week_developer_weekly_summaries(
        db_session,
        run_id="run-test-001",
        reference_date=date(2026, 3, 30),
        use_llm=False,
    )
    assert generation["run_id"] == "run-test-001"
    assert generation["week_start"] == "2026-03-23"
    assert generation["generated_count"] == 1
    assert generation["trace_step_count"] >= 1
    assert isinstance(generation["trace_steps"], list)
    assert generation["trace_steps"][-1]["name"] == "finalize"

    cards = await get_cached_developer_weekly_cards(
        db_session,
        anchor_date=date(2026, 3, 25),
        limit=10,
    )
    assert cards is not None
    assert cards["count"] == 1
    assert cards["results"][0]["owner"] == "alice"
    assert cards["results"][0]["total_findings"] == 1
    assert cards["results"][0]["raw_total_findings"] == 2

    detail = await get_cached_developer_weekly_report(
        db_session,
        owner="alice",
        anchor_date=date(2026, 3, 25),
    )
    assert detail is not None
    assert detail["owner"] == "alice"
    assert detail["summary"]["total_findings"] == 1
    assert detail["summary"]["raw_total_findings"] == 2
    assert detail["source"] == "heuristic"
