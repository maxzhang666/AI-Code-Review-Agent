from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from app.models import (
    MRFeedbackRecord,
    MergeRequestReview,
    Project,
    ProjectIgnoreStrategy,
    ReviewFinding,
    ReviewFindingAction,
)


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


@pytest.mark.asyncio
async def test_get_ignore_strategy_weekly_report_preview(client, db_session) -> None:
    project = Project(
        project_id=8802,
        project_name="ignore-report-demo",
        project_path="group/ignore-report-demo",
        project_url="https://gitlab.example.com/group/ignore-report-demo.git",
        namespace="group",
        review_enabled=True,
    )
    db_session.add(project)
    await db_session.flush()

    review = MergeRequestReview(
        project_id=8802,
        project_name="ignore-report-demo",
        merge_request_iid=32,
        merge_request_title="feat: ignore strategy report",
        source_branch="feature/a",
        target_branch="main",
        author_name="dev",
        author_email="dev@example.com",
        status="completed",
    )
    db_session.add(review)
    await db_session.flush()

    finding = ReviewFinding(
        review_id=review.id,
        issue_id="I-8",
        fingerprint="fp-ignore-report-1",
        category="quality",
        subcategory="naming",
        severity="low",
        file_path="src/core/naming.py",
        message="命名建议",
    )
    db_session.add(finding)
    await db_session.flush()

    for day in [4, 6, 13, 20, 27]:
        db_session.add(
            ReviewFindingAction(
                finding_id=finding.id,
                action_type="ignored",
                actor="admin",
                ignore_reason_code="rule_false_positive",
                action_at=datetime(2026, 3, day, 10, 0, 0),
            )
        )
    await db_session.commit()

    response = await client.get(
        "/api/webhook/reports/ignore-strategies/weekly/",
        params={"project_id": 8802, "anchor_date": "2026-03-30", "apply_changes": "false"},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["summary"]["project_count"] == 1
    assert payload["summary"]["eligible_count"] >= 1
    assert payload["summary"]["activated_count"] == 0


@pytest.mark.asyncio
async def test_list_project_ignore_strategies_returns_rows(client, db_session) -> None:
    db_session.add_all(
        [
            Project(
                project_id=8803,
                project_name="ignore-strategy-list",
                project_path="group/ignore-strategy-list",
                project_url="https://gitlab.example.com/group/ignore-strategy-list.git",
                namespace="group",
                review_enabled=True,
            ),
            ProjectIgnoreStrategy(
                project_id=8803,
                rule_key="quality.naming",
                path_pattern="src/**",
                signature="quality.naming|src/**",
                title="命名策略",
                status="active",
                sample_count_4w=8,
                active_weeks_4w=4,
                confidence_score=0.91,
                effective_at=datetime(2026, 3, 20, 10, 0, 0),
                expire_at=datetime(2026, 4, 3, 10, 0, 0),
            ),
            ProjectIgnoreStrategy(
                project_id=8803,
                rule_key="style.comment",
                path_pattern=None,
                signature="style.comment|*",
                title="注释策略",
                status="disabled",
                sample_count_4w=5,
                active_weeks_4w=2,
                confidence_score=0.79,
                effective_at=datetime(2026, 3, 12, 10, 0, 0),
                expire_at=datetime(2026, 3, 26, 10, 0, 0),
                disabled_at=datetime(2026, 3, 22, 10, 0, 0),
                disabled_reason="manual",
            ),
        ]
    )
    await db_session.commit()

    response = await client.get(
        "/api/webhook/reports/ignore-strategies/",
        params={"project_id": 8803},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert payload["results"][0]["rule_key"] == "quality.naming"
    assert payload["results"][1]["status"] == "disabled"


@pytest.mark.asyncio
async def test_list_project_ignore_strategies_supports_status_filter(client, db_session) -> None:
    db_session.add_all(
        [
            ProjectIgnoreStrategy(
                project_id=8807,
                rule_key="quality.naming",
                path_pattern="src/**",
                signature="quality.naming|src/**",
                title="命名策略",
                status="active",
                sample_count_4w=8,
                active_weeks_4w=4,
                confidence_score=0.91,
            ),
            ProjectIgnoreStrategy(
                project_id=8807,
                rule_key="style.comment",
                path_pattern=None,
                signature="style.comment|*",
                title="注释策略",
                status="disabled",
                sample_count_4w=5,
                active_weeks_4w=2,
                confidence_score=0.79,
            ),
        ]
    )
    await db_session.commit()

    response = await client.get(
        "/api/webhook/reports/ignore-strategies/",
        params=[("project_id", 8807), ("statuses", "active")],
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert payload["results"][0]["status"] == "active"
    assert payload["results"][0]["rule_key"] == "quality.naming"


@pytest.mark.asyncio
async def test_disable_ignore_strategy_updates_status(client, db_session) -> None:
    strategy = ProjectIgnoreStrategy(
        project_id=8804,
        rule_key="quality.naming",
        path_pattern="src/**",
        signature="quality.naming|src/**",
        title="命名策略",
        status="active",
        sample_count_4w=7,
        active_weeks_4w=3,
        confidence_score=0.87,
        effective_at=datetime(2026, 3, 20, 10, 0, 0),
        expire_at=datetime(2026, 4, 3, 10, 0, 0),
    )
    db_session.add(strategy)
    await db_session.commit()
    await db_session.refresh(strategy)

    response = await client.patch(
        f"/api/webhook/reports/ignore-strategies/{strategy.id}/disable/",
        json={"reason": "manual disable"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == strategy.id
    assert payload["status"] == "disabled"
    assert payload["disabled_reason"] == "manual disable"

    await db_session.refresh(strategy)
    assert strategy.status == "disabled"
    assert strategy.disabled_reason == "manual disable"
    assert strategy.disabled_at is not None


@pytest.mark.asyncio
async def test_disable_all_ignore_strategies_for_project(client, db_session) -> None:
    db_session.add_all(
        [
            ProjectIgnoreStrategy(
                project_id=8805,
                rule_key="quality.naming",
                path_pattern="src/**",
                signature="quality.naming|src/**",
                title="命名策略",
                status="active",
                sample_count_4w=7,
                active_weeks_4w=3,
                confidence_score=0.82,
            ),
            ProjectIgnoreStrategy(
                project_id=8805,
                rule_key="style.comment",
                path_pattern=None,
                signature="style.comment|*",
                title="注释策略",
                status="active",
                sample_count_4w=6,
                active_weeks_4w=3,
                confidence_score=0.8,
            ),
            ProjectIgnoreStrategy(
                project_id=8806,
                rule_key="style.comment",
                path_pattern=None,
                signature="style.comment|*",
                title="其他仓库策略",
                status="active",
                sample_count_4w=6,
                active_weeks_4w=3,
                confidence_score=0.8,
            ),
        ]
    )
    await db_session.commit()

    response = await client.post(
        "/api/webhook/reports/ignore-strategies/disable-all/",
        json={"project_id": 8805, "reason": "project cleanup"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == 8805
    assert payload["disabled_count"] == 2

    rows_8805 = (
        await db_session.execute(
            select(ProjectIgnoreStrategy).where(ProjectIgnoreStrategy.project_id == 8805)
        )
    ).scalars().all()
    assert all(item.status == "disabled" for item in rows_8805)
    assert all(item.disabled_reason == "project cleanup" for item in rows_8805)

    other = (
        await db_session.execute(
            select(ProjectIgnoreStrategy).where(ProjectIgnoreStrategy.project_id == 8806).limit(1)
        )
    ).scalars().first()
    assert other is not None
    assert other.status == "active"
