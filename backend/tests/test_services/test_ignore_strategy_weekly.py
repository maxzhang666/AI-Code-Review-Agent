from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import MergeRequestReview, Project, ProjectIgnoreStrategy, ReviewFinding, ReviewFindingAction
from app.services.reporting.ignore_strategy_weekly import (
    build_ignore_strategy_prompt_for_project,
    generate_ignore_strategy_weekly_report,
)


@pytest.mark.asyncio
async def test_generate_ignore_strategy_weekly_report_applies_eligible_candidates(db_session) -> None:
    project = Project(
        project_id=8801,
        project_name="ignore-strategy-demo",
        project_path="team/ignore-strategy-demo",
        project_url="https://gitlab.example.com/team/ignore-strategy-demo.git",
        namespace="team",
        review_enabled=True,
    )
    db_session.add(project)
    await db_session.flush()

    review = MergeRequestReview(
        project_id=project.project_id,
        project_name=project.project_name,
        merge_request_iid=11,
        merge_request_title="feat: ignore strategy seed",
        source_branch="feature/ignore-strategy",
        target_branch="main",
        author_name="lead",
        author_email="lead@example.com",
        status="completed",
    )
    db_session.add(review)
    await db_session.flush()

    quality_finding = ReviewFinding(
        review_id=review.id,
        issue_id="I-11",
        fingerprint="fp-ignore-quality",
        category="quality",
        subcategory="naming",
        severity="low",
        file_path="src/service/handler.py",
        message="命名过长可读性一般",
    )
    security_finding = ReviewFinding(
        review_id=review.id,
        issue_id="I-22",
        fingerprint="fp-ignore-security",
        category="security",
        subcategory="auth",
        severity="high",
        file_path="src/security/auth.py",
        message="鉴权链路存在风险",
    )
    db_session.add_all([quality_finding, security_finding])
    await db_session.flush()

    action_times = [
        datetime(2026, 3, 5, 10, 0, 0),
        datetime(2026, 3, 6, 10, 0, 0),
        datetime(2026, 3, 12, 10, 0, 0),
        datetime(2026, 3, 19, 10, 0, 0),
        datetime(2026, 3, 26, 10, 0, 0),
    ]
    for idx, action_at in enumerate(action_times, start=1):
        db_session.add(
            ReviewFindingAction(
                finding_id=quality_finding.id,
                action_type="ignored",
                actor="admin",
                note=f"bulk-ignore-{idx}",
                ignore_reason_code="rule_false_positive",
                action_at=action_at,
            )
        )

    db_session.add(
        ReviewFindingAction(
            finding_id=security_finding.id,
            action_type="ignored",
            actor="admin",
            note="security-ignore",
            ignore_reason_code="business_exception",
            action_at=datetime(2026, 3, 20, 10, 0, 0),
        )
    )
    await db_session.commit()

    report = await generate_ignore_strategy_weekly_report(
        db_session,
        anchor_date=date(2026, 3, 30),
        apply_changes=True,
    )

    assert report["summary"]["raw_ignored_actions"] == 6
    assert report["summary"]["high_risk_filtered"] == 1
    assert report["summary"]["eligible_count"] >= 1
    assert report["summary"]["activated_count"] >= 1
    assert report["projects"]

    strategy = (
        await db_session.execute(
            select(ProjectIgnoreStrategy).where(ProjectIgnoreStrategy.project_id == project.project_id)
        )
    ).scalars().first()
    assert strategy is not None
    assert strategy.status == "active"
    assert strategy.sample_count_4w == 5
    assert strategy.active_weeks_4w >= 2
    assert strategy.confidence_score >= 0.75


@pytest.mark.asyncio
async def test_generate_ignore_strategy_weekly_report_supports_preview_mode(db_session) -> None:
    project = Project(
        project_id=8802,
        project_name="ignore-strategy-preview",
        project_path="team/ignore-strategy-preview",
        project_url="https://gitlab.example.com/team/ignore-strategy-preview.git",
        namespace="team",
        review_enabled=True,
    )
    db_session.add(project)
    await db_session.flush()

    review = MergeRequestReview(
        project_id=project.project_id,
        project_name=project.project_name,
        merge_request_iid=12,
        merge_request_title="feat: preview mode",
        source_branch="feature/preview",
        target_branch="main",
        author_name="lead",
        author_email="lead@example.com",
        status="completed",
    )
    db_session.add(review)
    await db_session.flush()

    finding = ReviewFinding(
        review_id=review.id,
        issue_id="I-31",
        fingerprint="fp-ignore-preview",
        category="quality",
        subcategory="format",
        severity="low",
        file_path="src/preview/format.py",
        message="格式化建议",
    )
    db_session.add(finding)
    await db_session.flush()

    for offset_days in [1, 2, 8, 15, 22]:
        db_session.add(
            ReviewFindingAction(
                finding_id=finding.id,
                action_type="ignored",
                actor="admin",
                ignore_reason_code="historical_debt",
                action_at=datetime(2026, 3, 30, 9, 0, 0) - timedelta(days=offset_days),
            )
        )
    await db_session.commit()

    report = await generate_ignore_strategy_weekly_report(
        db_session,
        project_id=project.project_id,
        anchor_date=date(2026, 3, 30),
        apply_changes=False,
    )

    assert report["summary"]["eligible_count"] >= 1
    assert report["summary"]["activated_count"] == 0

    strategies = (
        await db_session.execute(
            select(ProjectIgnoreStrategy).where(ProjectIgnoreStrategy.project_id == project.project_id)
        )
    ).scalars().all()
    assert strategies == []


@pytest.mark.asyncio
async def test_build_ignore_strategy_prompt_for_project_uses_active_rows(db_session) -> None:
    db_session.add(
        ProjectIgnoreStrategy(
            project_id=8803,
            rule_key="quality.naming",
            path_pattern="src/**",
            signature="quality.naming|src/**",
            ignore_condition="命中后可降级为忽略级提示。",
            sample_count_4w=6,
            active_weeks_4w=3,
            confidence_score=0.82,
            status="active",
            effective_at=datetime(2026, 3, 20, 8, 0, 0),
            expire_at=datetime(2026, 4, 10, 8, 0, 0),
        )
    )
    await db_session.commit()

    prompt = await build_ignore_strategy_prompt_for_project(
        db_session,
        project_id=8803,
        now=datetime(2026, 3, 30, 9, 0, 0),
    )
    assert "仓库级忽略级策略" in prompt
    assert "quality.naming" in prompt
    assert "src/**" in prompt
