from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.models import MergeRequestReview, ReviewFinding, ReviewFindingAction


async def _create_review(db_session, *, project_id: int, status: str, author_name: str, author_email: str) -> MergeRequestReview:
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
        review_issues=[],
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
