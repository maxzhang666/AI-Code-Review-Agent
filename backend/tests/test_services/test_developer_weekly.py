from __future__ import annotations

from datetime import date, datetime

import pytest

from app.models import MRFeedbackRecord, MergeRequestReview, Project, ReviewFinding
from app.services.reporting import generate_developer_weekly_report


@pytest.mark.asyncio
async def test_generate_developer_weekly_report_by_owner(db_session) -> None:
    project = Project(
        project_id=7601,
        project_name="dev-weekly",
        project_path="team/dev-weekly",
        project_url="https://gitlab.example.com/team/dev-weekly.git",
        namespace="team",
        review_enabled=True,
    )
    db_session.add(project)
    await db_session.flush()

    review = MergeRequestReview(
        project_id=7601,
        project_name="dev-weekly",
        merge_request_iid=18,
        merge_request_title="MR-18",
        source_branch="feat/demo",
        target_branch="main",
        author_name="dev",
        author_email="dev@example.com",
        created_at=datetime(2026, 3, 24, 10, 0, 0),
        status="completed",
        total_files=2,
    )
    db_session.add(review)
    await db_session.flush()

    db_session.add_all(
        [
            ReviewFinding(
                review_id=review.id,
                fingerprint="dev-f-1",
                category="quality",
                severity="high",
                file_path="src/service.py",
                owner_name="alice",
                owner_email="alice@example.com",
                created_at=datetime(2026, 3, 24, 10, 5, 0),
            ),
            ReviewFinding(
                review_id=review.id,
                fingerprint="dev-f-2",
                category="style",
                severity="low",
                file_path="src/service.py",
                owner_name="alice",
                owner_email="alice@example.com",
                created_at=datetime(2026, 3, 24, 10, 6, 0),
            ),
            ReviewFinding(
                review_id=review.id,
                fingerprint="dev-f-3",
                category="security",
                severity="medium",
                file_path="src/other.py",
                owner_name="bob",
                owner_email="bob@example.com",
                created_at=datetime(2026, 3, 24, 10, 7, 0),
            ),
        ]
    )

    db_session.add(
        MRFeedbackRecord(
            project_id=7601,
            merge_request_iid=18,
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

    report = await generate_developer_weekly_report(
        db_session,
        owner="alice",
        anchor_date=date(2026, 3, 25),
    )

    assert report["week_start"] == "2026-03-23"
    assert report["summary"]["total_findings"] == 2
    assert report["summary"]["total_reviews"] == 1
    assert report["summary"]["ignore_actions"] == 1
    assert report["summary"]["reopen_actions"] == 0
    assert report["by_category"][0]["name"] == "quality"
    assert report["top_files"][0]["name"] == "src/service.py"
    assert "alice" in report["available_owners"]
    assert report["ai_summary"]
    assert report["gap_checklist"]


@pytest.mark.asyncio
async def test_generate_developer_weekly_report_excludes_ignored_findings_by_default(db_session) -> None:
    project = Project(
        project_id=7602,
        project_name="dev-weekly-status",
        project_path="team/dev-weekly-status",
        project_url="https://gitlab.example.com/team/dev-weekly-status.git",
        namespace="team",
        review_enabled=True,
    )
    db_session.add(project)
    await db_session.flush()

    review = MergeRequestReview(
        project_id=7602,
        project_name="dev-weekly-status",
        merge_request_iid=28,
        merge_request_title="MR-28",
        source_branch="feat/status",
        target_branch="main",
        author_name="dev",
        author_email="dev@example.com",
        created_at=datetime(2026, 3, 24, 10, 0, 0),
        status="completed",
        total_files=2,
    )
    db_session.add(review)
    await db_session.flush()

    db_session.add_all(
        [
            ReviewFinding(
                review_id=review.id,
                issue_id="I-1",
                fingerprint="dev-status-f-1",
                category="quality",
                severity="high",
                file_path="src/service.py",
                owner_name="alice",
                owner_email="alice@example.com",
                created_at=datetime(2026, 3, 24, 10, 5, 0),
            ),
            ReviewFinding(
                review_id=review.id,
                issue_id="I-2",
                fingerprint="dev-status-f-2",
                category="style",
                severity="low",
                file_path="src/service.py",
                owner_name="alice",
                owner_email="alice@example.com",
                created_at=datetime(2026, 3, 24, 10, 6, 0),
            ),
        ]
    )

    db_session.add(
        MRFeedbackRecord(
            project_id=7602,
            merge_request_iid=28,
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

    report_default = await generate_developer_weekly_report(
        db_session,
        owner="alice",
        anchor_date=date(2026, 3, 25),
    )
    assert report_default["include_statuses"] == ["open", "reopened"]
    assert report_default["summary"]["raw_total_findings"] == 2
    assert report_default["summary"]["total_findings"] == 1
    assert report_default["by_category"] == [{"name": "style", "value": 1}]

    report_with_ignored = await generate_developer_weekly_report(
        db_session,
        owner="alice",
        anchor_date=date(2026, 3, 25),
        include_statuses=["open", "reopened", "ignored"],
    )
    assert report_with_ignored["include_statuses"] == ["open", "ignored", "reopened"]
    assert report_with_ignored["summary"]["raw_total_findings"] == 2
    assert report_with_ignored["summary"]["total_findings"] == 2
