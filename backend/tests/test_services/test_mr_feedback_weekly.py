from __future__ import annotations

from datetime import date, datetime

import pytest

from app.models import MRFeedbackRecord, MergeRequestReview, Project, ReviewFinding
from app.services.reporting import generate_mr_feedback_weekly_report


def _build_review(project_id: int, project_name: str, iid: int, created_at: datetime) -> MergeRequestReview:
    return MergeRequestReview(
        project_id=project_id,
        project_name=project_name,
        merge_request_iid=iid,
        merge_request_title=f"MR-{iid}",
        source_branch="feature/a",
        target_branch="main",
        author_name="dev",
        author_email="dev@example.com",
        created_at=created_at,
        status="completed",
        total_files=1,
    )


@pytest.mark.asyncio
async def test_generate_mr_feedback_weekly_report_aggregates_team_and_projects(db_session) -> None:
    project_alpha = Project(
        project_id=1001,
        project_name="alpha-service",
        project_path="team/alpha-service",
        project_url="https://gitlab.example.com/team/alpha-service.git",
        namespace="team",
        review_enabled=True,
    )
    project_beta = Project(
        project_id=1002,
        project_name="beta-service",
        project_path="team/beta-service",
        project_url="https://gitlab.example.com/team/beta-service.git",
        namespace="team",
        review_enabled=True,
    )
    db_session.add_all([project_alpha, project_beta])
    await db_session.flush()

    review_alpha = _build_review(1001, "alpha-service", 11, datetime(2026, 3, 24, 9, 0, 0))
    review_beta = _build_review(1002, "beta-service", 15, datetime(2026, 3, 24, 10, 0, 0))
    db_session.add_all([review_alpha, review_beta])
    await db_session.flush()

    db_session.add_all(
        [
            ReviewFinding(
                review_id=review_alpha.id,
                fingerprint="f-alpha-1",
                category="security",
                severity="high",
                created_at=datetime(2026, 3, 24, 10, 1, 0),
            ),
            ReviewFinding(
                review_id=review_alpha.id,
                fingerprint="f-alpha-2",
                category="quality",
                severity="medium",
                created_at=datetime(2026, 3, 24, 10, 2, 0),
            ),
            ReviewFinding(
                review_id=review_beta.id,
                fingerprint="f-beta-1",
                category="style",
                severity="low",
                created_at=datetime(2026, 3, 25, 12, 0, 0),
            ),
        ]
    )

    db_session.add_all(
        [
            MRFeedbackRecord(
                project_id=1001,
                merge_request_iid=11,
                review_id=review_alpha.id,
                issue_id="I-1",
                rule_key="security.auth",
                action="ignore",
                reason="误报，工具噪音",
                operator_gitlab_id=501,
                operator_name="Lead A",
                operator_role="maintainer",
                source_note_id=2001,
                source_note_body="/cra ignore I-1 reason: 误报",
                created_at=datetime(2026, 3, 24, 12, 0, 0),
            ),
            MRFeedbackRecord(
                project_id=1001,
                merge_request_iid=11,
                review_id=review_alpha.id,
                issue_id="I-2",
                rule_key="security.auth",
                action="ignore",
                reason="历史包袱，老代码暂不改",
                operator_gitlab_id=501,
                operator_name="Lead A",
                operator_role="maintainer",
                source_note_id=2002,
                source_note_body="/cra ignore I-2 reason: 历史包袱",
                created_at=datetime(2026, 3, 24, 12, 10, 0),
            ),
            MRFeedbackRecord(
                project_id=1001,
                merge_request_iid=11,
                review_id=review_alpha.id,
                issue_id="I-2",
                rule_key="security.auth",
                action="reopen",
                reason="已进入重构排期，恢复跟踪",
                operator_gitlab_id=501,
                operator_name="Lead A",
                operator_role="maintainer",
                source_note_id=2003,
                source_note_body="/cra reopen I-2 reason: 重构排期",
                created_at=datetime(2026, 3, 25, 9, 0, 0),
            ),
            MRFeedbackRecord(
                project_id=1002,
                merge_request_iid=15,
                review_id=review_beta.id,
                issue_id="I-7",
                rule_key=None,
                action="ignore",
                reason="业务特例，客户要求",
                operator_gitlab_id=502,
                operator_name="Lead B",
                operator_role="owner",
                source_note_id=2004,
                source_note_body="/cra ignore I-7 reason: 业务特例",
                created_at=datetime(2026, 3, 26, 12, 0, 0),
            ),
            MRFeedbackRecord(
                project_id=1002,
                merge_request_iid=15,
                review_id=review_beta.id,
                issue_id="I-8",
                rule_key="style.naming",
                action="ignore",
                reason="计划下个迭代修复",
                operator_gitlab_id=502,
                operator_name="Lead B",
                operator_role="owner",
                source_note_id=2005,
                source_note_body="/cra ignore I-8 reason: 下个迭代修复",
                created_at=datetime(2026, 3, 27, 10, 0, 0),
            ),
            MRFeedbackRecord(
                project_id=1002,
                merge_request_iid=15,
                review_id=review_beta.id,
                issue_id="I-99",
                rule_key="style.naming",
                action="ignore",
                reason="历史记录，周外数据",
                operator_gitlab_id=502,
                operator_name="Lead B",
                operator_role="owner",
                source_note_id=2006,
                source_note_body="/cra ignore I-99 reason: 周外",
                created_at=datetime(2026, 3, 30, 8, 0, 0),
            ),
        ]
    )
    await db_session.commit()

    report = await generate_mr_feedback_weekly_report(
        db_session,
        anchor_date=date(2026, 3, 25),
    )

    assert report["week_start"] == "2026-03-23"
    assert report["week_end"] == "2026-03-29"
    assert report["summary"]["total_issues"] == 3
    assert report["summary"]["ignored_count"] == 4
    assert report["summary"]["reopened_count"] == 1
    assert report["summary"]["feedback_actions"] == 5
    assert report["summary"]["ignore_rate"] == 0.8

    assert report["top_ignored_rules"][0]["rule_key"] == "security.auth"
    assert report["top_ignored_rules"][0]["ignore_count"] == 2

    reason_map = {item["reason_type"]: item["count"] for item in report["ignore_reason_distribution"]}
    assert reason_map["历史包袱"] == 1
    assert reason_map["业务特例"] == 1
    assert reason_map["误报"] == 1
    assert reason_map["已规划后续修复"] == 1

    project_map = {item["project_id"]: item for item in report["projects"]}
    assert project_map[1001]["project_name"] == "alpha-service"
    assert project_map[1001]["total_issues"] == 2
    assert project_map[1001]["ignored_count"] == 2
    assert project_map[1001]["reopened_count"] == 1
    assert project_map[1002]["project_name"] == "beta-service"
    assert project_map[1002]["total_issues"] == 1
    assert project_map[1002]["ignored_count"] == 2
    assert project_map[1002]["reopened_count"] == 0

    assert report["suggested_policy_changes"]
    assert any("弱提醒" in suggestion for suggestion in report["suggested_policy_changes"])


@pytest.mark.asyncio
async def test_generate_mr_feedback_weekly_report_supports_project_filter(db_session) -> None:
    project_alpha = Project(
        project_id=1201,
        project_name="alpha-only",
        project_path="team/alpha-only",
        project_url="https://gitlab.example.com/team/alpha-only.git",
        namespace="team",
        review_enabled=True,
    )
    db_session.add(project_alpha)
    await db_session.flush()

    review_alpha = _build_review(1201, "alpha-only", 5, datetime(2026, 3, 26, 10, 0, 0))
    db_session.add(review_alpha)
    await db_session.flush()

    db_session.add(
        ReviewFinding(
            review_id=review_alpha.id,
            fingerprint="f-alpha-only-1",
            category="quality",
            severity="medium",
            created_at=datetime(2026, 3, 26, 10, 10, 0),
        )
    )
    db_session.add(
        MRFeedbackRecord(
            project_id=1201,
            merge_request_iid=5,
            review_id=review_alpha.id,
            issue_id="I-1",
            rule_key=None,
            action="ignore",
            reason="误报",
            operator_gitlab_id=901,
            operator_name="Lead",
            operator_role="maintainer",
            source_note_id=3001,
            source_note_body="/cra ignore I-1 reason: 误报",
            created_at=datetime(2026, 3, 26, 11, 0, 0),
        )
    )
    await db_session.commit()

    report = await generate_mr_feedback_weekly_report(
        db_session,
        project_id=1201,
        anchor_date=date(2026, 3, 27),
    )

    assert report["summary"]["total_issues"] == 1
    assert report["summary"]["ignored_count"] == 1
    assert report["summary"]["reopened_count"] == 0
    assert len(report["projects"]) == 1
    assert report["projects"][0]["project_id"] == 1201

