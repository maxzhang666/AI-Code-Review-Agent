from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.models import MergeRequestReview, ReviewFinding, ReviewFindingAction


async def _create_review(
    db_session,
    *,
    project_id: int,
    status: str,
    author_name: str,
    author_email: str,
    review_issues: list[dict] | None = None,
) -> MergeRequestReview:
    review = MergeRequestReview(
        project_id=project_id,
        project_name=f"project-{project_id}",
        merge_request_iid=project_id,
        merge_request_title=f"mr-{project_id}",
        source_branch="feature/x",
        target_branch="main",
        author_name=author_name,
        author_email=author_email,
        review_content="review",
        status=status,
        review_issues=review_issues if review_issues is not None else [],
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)
    return review


async def _create_finding(
    db_session,
    *,
    review_id: int,
    severity: str,
    message: str,
    created_at: datetime,
) -> ReviewFinding:
    finding = ReviewFinding(
        review_id=review_id,
        issue_id="",
        fingerprint=f"fp-{review_id}-{severity}-{message}",
        category="quality",
        subcategory="",
        severity=severity,
        confidence=0.8,
        file_path="src/service.py",
        line_start=10,
        line_end=11,
        message=message,
        suggestion="fix",
        code_snippet="bad()",
        owner_name="owner",
        owner_email="owner@example.com",
        owner="owner",
        is_blocking=False,
        is_false_positive=False,
        created_at=created_at,
        updated_at=created_at,
    )
    db_session.add(finding)
    await db_session.commit()
    await db_session.refresh(finding)
    return finding


async def _create_action(
    db_session,
    *,
    finding_id: int,
    action_type: str,
    actor: str,
    action_at: datetime,
    note: str = "",
) -> ReviewFindingAction:
    action = ReviewFindingAction(
        finding_id=finding_id,
        action_type=action_type,
        actor=actor,
        note=note,
        action_at=action_at,
    )
    db_session.add(action)
    await db_session.commit()
    await db_session.refresh(action)
    return action


@pytest.mark.asyncio
async def test_workbench_list_supports_unprocessed_action_status_filter(client, db_session) -> None:
    base_time = datetime(2026, 3, 1, 8, 0, 0)
    review = await _create_review(
        db_session,
        project_id=8010,
        status="completed",
        author_name="Alice",
        author_email="alice@example.com",
    )
    unprocessed = await _create_finding(
        db_session,
        review_id=review.id,
        severity="high",
        message="unprocessed finding",
        created_at=base_time,
    )
    fixed = await _create_finding(
        db_session,
        review_id=review.id,
        severity="medium",
        message="fixed finding",
        created_at=base_time + timedelta(minutes=1),
    )
    await _create_action(
        db_session,
        finding_id=fixed.id,
        action_type="fixed",
        actor="bob",
        action_at=base_time + timedelta(minutes=2),
        note="done",
    )

    resp_unprocessed = await client.get(
        "/api/webhook/review-findings/",
        params={"action_statuses": ["unprocessed"]},
    )
    assert resp_unprocessed.status_code == 200
    payload_unprocessed = resp_unprocessed.json()
    ids_unprocessed = {item["id"] for item in payload_unprocessed["results"]}
    assert unprocessed.id in ids_unprocessed
    assert fixed.id not in ids_unprocessed
    result_unprocessed = next(item for item in payload_unprocessed["results"] if item["id"] == unprocessed.id)
    assert result_unprocessed["action_status"] == "unprocessed"
    assert result_unprocessed["latest_action"] is None

    resp_fixed = await client.get(
        "/api/webhook/review-findings/",
        params={"action_statuses": ["fixed"]},
    )
    assert resp_fixed.status_code == 200
    payload_fixed = resp_fixed.json()
    ids_fixed = {item["id"] for item in payload_fixed["results"]}
    assert fixed.id in ids_fixed
    assert unprocessed.id not in ids_fixed
    result_fixed = next(item for item in payload_fixed["results"] if item["id"] == fixed.id)
    assert result_fixed["action_status"] == "fixed"
    assert result_fixed["latest_action"]["actor"] == "bob"


@pytest.mark.asyncio
async def test_workbench_list_supports_core_filters(client, db_session) -> None:
    base_time = datetime(2026, 3, 10, 10, 0, 0)
    review_match = await _create_review(
        db_session,
        project_id=9001,
        status="completed",
        author_name="Target Author",
        author_email="target@example.com",
    )
    review_other = await _create_review(
        db_session,
        project_id=9002,
        status="failed",
        author_name="Other Author",
        author_email="other@example.com",
    )
    matched = await _create_finding(
        db_session,
        review_id=review_match.id,
        severity="critical",
        message="keep-me",
        created_at=base_time,
    )
    _ = await _create_finding(
        db_session,
        review_id=review_other.id,
        severity="low",
        message="drop-me",
        created_at=base_time,
    )

    resp = await client.get(
        "/api/webhook/review-findings/",
        params={
            "project_id": 9001,
            "severities": ["critical"],
            "review_statuses": ["completed"],
            "author": "target@example.com",
            "start_at": (base_time - timedelta(minutes=1)).isoformat(),
            "end_at": (base_time + timedelta(minutes=1)).isoformat(),
        },
    )

    assert resp.status_code == 200
    payload = resp.json()
    assert payload["count"] == 1
    assert payload["total"] == 1
    assert len(payload["results"]) == 1
    result = payload["results"][0]
    assert result["id"] == matched.id
    assert result["review"]["project_id"] == 9001
    assert result["review"]["status"] == "completed"


@pytest.mark.asyncio
async def test_workbench_batch_actions_returns_success_and_failed_counts(client, db_session) -> None:
    base_time = datetime(2026, 3, 15, 11, 0, 0)
    review = await _create_review(
        db_session,
        project_id=9100,
        status="completed",
        author_name="Batch Tester",
        author_email="batch@example.com",
    )
    finding1 = await _create_finding(
        db_session,
        review_id=review.id,
        severity="high",
        message="finding-1",
        created_at=base_time,
    )
    finding2 = await _create_finding(
        db_session,
        review_id=review.id,
        severity="medium",
        message="finding-2",
        created_at=base_time + timedelta(minutes=1),
    )

    response = await client.post(
        "/api/webhook/review-findings/actions/batch/",
        json={
            "finding_ids": [finding1.id, finding2.id, 999999],
            "action_type": "todo",
            "actor": "triager",
            "note": "bulk action",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success_count"] == 2
    assert payload["failed_count"] == 1
    assert sorted(payload["failed_ids"]) == [999999]

    check = await client.get(
        "/api/webhook/review-findings/",
        params={"action_statuses": ["todo"], "project_id": 9100},
    )
    assert check.status_code == 200
    ids = {item["id"] for item in check.json()["results"]}
    assert finding1.id in ids
    assert finding2.id in ids


@pytest.mark.asyncio
async def test_workbench_list_rejects_invalid_action_statuses(client) -> None:
    response = await client.get(
        "/api/webhook/review-findings/",
        params={"action_statuses": ["fixed", "invalid-status"]},
    )

    assert response.status_code == 422
    payload = response.json()
    detail = str(payload.get("detail") or payload.get("message") or payload)
    assert "action_statuses" in detail
    assert "invalid-status" in detail
    assert "unprocessed" in detail
    assert "fixed" in detail
    assert "todo" in detail
    assert "ignored" in detail
    assert "reopened" in detail


@pytest.mark.asyncio
async def test_workbench_batch_actions_rejects_too_many_finding_ids(client) -> None:
    response = await client.post(
        "/api/webhook/review-findings/actions/batch/",
        json={
            "finding_ids": list(range(1, 503)),
            "action_type": "todo",
            "actor": "triager",
            "note": "bulk action",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_workbench_list_uses_newest_action_as_latest_status(client, db_session) -> None:
    base_time = datetime(2026, 3, 20, 9, 0, 0)
    review = await _create_review(
        db_session,
        project_id=9200,
        status="completed",
        author_name="Latest Action Tester",
        author_email="latest@example.com",
    )
    finding = await _create_finding(
        db_session,
        review_id=review.id,
        severity="high",
        message="latest-action-ordering",
        created_at=base_time,
    )
    await _create_action(
        db_session,
        finding_id=finding.id,
        action_type="todo",
        actor="alice",
        action_at=base_time + timedelta(minutes=1),
        note="older action",
    )
    await _create_action(
        db_session,
        finding_id=finding.id,
        action_type="fixed",
        actor="bob",
        action_at=base_time + timedelta(minutes=2),
        note="newer action",
    )

    response = await client.get(
        "/api/webhook/review-findings/",
        params={"project_id": 9200},
    )

    assert response.status_code == 200
    result = next(item for item in response.json()["results"] if item["id"] == finding.id)
    assert result["action_status"] == "fixed"
    assert result["latest_action"]["action_type"] == "fixed"
    assert result["latest_action"]["actor"] == "bob"
    assert result["latest_action"]["note"] == "newer action"


@pytest.mark.asyncio
async def test_workbench_list_materializes_legacy_review_issues(client, db_session) -> None:
    review = await _create_review(
        db_session,
        project_id=9300,
        status="completed",
        author_name="Legacy Author",
        author_email="legacy@example.com",
        review_issues=[
            {
                "severity": "high",
                "category": "bug",
                "file": "src/legacy.py",
                "line": 18,
                "description": "legacy issue not yet materialized",
                "suggestion": "guard access",
            }
        ],
    )

    before = (
        await db_session.execute(
            select(ReviewFinding.id).where(ReviewFinding.review_id == review.id)
        )
    ).scalars().all()
    assert before == []

    response = await client.get(
        "/api/webhook/review-findings/",
        params={"project_id": 9300},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert any(item["review"]["id"] == review.id for item in payload["results"])

    after = (
        await db_session.execute(
            select(ReviewFinding.id).where(ReviewFinding.review_id == review.id)
        )
    ).scalars().all()
    assert len(after) == 1


@pytest.mark.asyncio
async def test_workbench_list_materializes_legacy_issues_beyond_first_scan_window(client, db_session) -> None:
    project_id = 9400
    base_time = datetime(2026, 3, 25, 8, 0, 0)
    empty_reviews: list[MergeRequestReview] = []
    for idx in range(220):
        ts = base_time + timedelta(minutes=idx)
        empty_reviews.append(
            MergeRequestReview(
                project_id=project_id,
                project_name=f"project-{project_id}",
                merge_request_iid=10000 + idx,
                merge_request_title=f"empty-{idx}",
                source_branch="feature/empty",
                target_branch="main",
                author_name="Empty Author",
                author_email="empty@example.com",
                review_content="review",
                status="completed",
                review_issues=[],
                created_at=ts,
                updated_at=ts,
            )
        )
    legacy_ts = base_time - timedelta(days=2)
    legacy_review = MergeRequestReview(
        project_id=project_id,
        project_name=f"project-{project_id}",
        merge_request_iid=9999,
        merge_request_title="legacy-beyond-window",
        source_branch="feature/legacy",
        target_branch="main",
        author_name="Legacy Window Author",
        author_email="legacy-window@example.com",
        review_content="review",
        status="completed",
        review_issues=[
            {
                "severity": "high",
                "category": "bug",
                "file": "src/window.py",
                "line": 7,
                "description": "legacy beyond first window",
                "suggestion": "add guard",
            }
        ],
        created_at=legacy_ts,
        updated_at=legacy_ts,
    )
    db_session.add_all([*empty_reviews, legacy_review])
    await db_session.commit()
    await db_session.refresh(legacy_review)

    before = (
        await db_session.execute(
            select(ReviewFinding.id).where(ReviewFinding.review_id == legacy_review.id)
        )
    ).scalars().all()
    assert before == []

    response = await client.get(
        "/api/webhook/review-findings/",
        params={"project_id": project_id},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert any(item["review"]["id"] == legacy_review.id for item in payload["results"])

    after = (
        await db_session.execute(
            select(ReviewFinding.id).where(ReviewFinding.review_id == legacy_review.id)
        )
    ).scalars().all()
    assert len(after) == 1


@pytest.mark.asyncio
async def test_workbench_list_orders_by_review_created_at_desc(client, db_session) -> None:
    older_review_time = datetime(2026, 3, 20, 9, 0, 0)
    newer_review_time = datetime(2026, 3, 22, 9, 0, 0)

    older_review = MergeRequestReview(
        project_id=9500,
        project_name="project-9500",
        merge_request_iid=9500,
        merge_request_title="older-review",
        source_branch="feature/older",
        target_branch="main",
        author_name="Older",
        author_email="older@example.com",
        review_content="older",
        status="completed",
        review_issues=[],
        created_at=older_review_time,
        updated_at=older_review_time,
    )
    newer_review = MergeRequestReview(
        project_id=9500,
        project_name="project-9500",
        merge_request_iid=9501,
        merge_request_title="newer-review",
        source_branch="feature/newer",
        target_branch="main",
        author_name="Newer",
        author_email="newer@example.com",
        review_content="newer",
        status="completed",
        review_issues=[],
        created_at=newer_review_time,
        updated_at=newer_review_time,
    )
    db_session.add_all([older_review, newer_review])
    await db_session.commit()
    await db_session.refresh(older_review)
    await db_session.refresh(newer_review)

    # Intentionally make the older review's finding newer by finding timestamp
    # to verify ordering is based on review created_at.
    older_finding = await _create_finding(
        db_session,
        review_id=older_review.id,
        severity="high",
        message="older-review-finding",
        created_at=datetime(2026, 3, 23, 8, 0, 0),
    )
    newer_finding = await _create_finding(
        db_session,
        review_id=newer_review.id,
        severity="medium",
        message="newer-review-finding",
        created_at=datetime(2026, 3, 21, 8, 0, 0),
    )

    response = await client.get(
        "/api/webhook/review-findings/",
        params={"project_id": 9500, "limit": 20, "page": 1},
    )
    assert response.status_code == 200
    rows = response.json()["results"]
    ids = [item["id"] for item in rows if item["id"] in {older_finding.id, newer_finding.id}]
    assert ids[:2] == [newer_finding.id, older_finding.id]
