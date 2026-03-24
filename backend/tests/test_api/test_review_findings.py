from __future__ import annotations

import pytest

from app.models import MergeRequestReview


async def _create_review_with_issues(db_session) -> MergeRequestReview:
    review = MergeRequestReview(
        project_id=7001,
        project_name="demo-project",
        merge_request_iid=12,
        merge_request_title="feat: refine parser",
        source_branch="feature/refine-parser",
        target_branch="main",
        author_name="Alice",
        author_email="alice@example.com",
        review_content="structured review",
        status="completed",
        review_issues=[
            {
                "severity": "high",
                "category": "bug",
                "subcategory": "null-check",
                "file": "src/service.py",
                "line": 31,
                "line_end": 33,
                "description": "missing null guard",
                "suggestion": "add a None check before dereference",
                "code_snippet": "value = payload.get('data')\nreturn value['id']",
                "owner": "alice",
                "confidence": 0.95,
                "is_blocking": True,
            },
            {
                "severity": "low",
                "category": "style",
                "file": "src/service.py",
                "line": 78,
                "description": "log message can be clearer",
                "suggestion": "rename variable and improve wording",
                "owner": "alice",
            },
        ],
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)
    return review


@pytest.mark.asyncio
async def test_list_review_findings_materializes_legacy_issues(client, db_session) -> None:
    review = await _create_review_with_issues(db_session)

    response = await client.get(f"/api/webhook/reviews/{review.id}/findings/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 2
    assert len(payload["results"]) == 2

    first = payload["results"][0]
    assert first["review_id"] == review.id
    assert first["category"]
    assert first["severity"] in {"critical", "high", "medium", "low"}
    assert first["fingerprint"]
    assert any(
        item.get("code_snippet") == "value = payload.get('data')\nreturn value['id']"
        for item in payload["results"]
    )


@pytest.mark.asyncio
async def test_create_finding_action_and_stats(client, db_session) -> None:
    review = await _create_review_with_issues(db_session)

    findings_resp = await client.get(f"/api/webhook/reviews/{review.id}/findings/")
    assert findings_resp.status_code == 200
    findings = findings_resp.json()["results"]
    assert findings
    finding_id = int(findings[0]["id"])

    action_resp = await client.post(
        f"/api/webhook/review-findings/{finding_id}/actions/",
        json={"action_type": "fixed", "actor": "bob", "note": "addressed in follow-up commit"},
    )
    assert action_resp.status_code == 200
    action_payload = action_resp.json()
    assert action_payload["finding_id"] == finding_id
    assert action_payload["action_type"] == "fixed"
    assert action_payload["actor"] == "bob"

    stats_resp = await client.get("/api/webhook/review-findings/stats/")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_findings"] >= 2
    assert any(item["name"] == "bug" for item in stats["by_category"])
    assert any(item["name"] == "alice" for item in stats["by_owner"])


@pytest.mark.asyncio
async def test_findings_default_owner_prefers_author_name_over_email(client, db_session) -> None:
    review = MergeRequestReview(
        project_id=7002,
        project_name="demo-project-2",
        merge_request_iid=22,
        merge_request_title="fix: owner fallback",
        source_branch="feature/owner-fallback",
        target_branch="main",
        author_name="Alice Zhang",
        author_email="alice@example.com",
        review_content="structured review",
        status="completed",
        review_issues=[
            {
                "severity": "medium",
                "category": "quality",
                "file": "src/logic.py",
                "line": 10,
                "description": "naming can be improved",
                "suggestion": "rename variable",
            }
        ],
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)

    findings_resp = await client.get(f"/api/webhook/reviews/{review.id}/findings/")
    assert findings_resp.status_code == 200
    findings = findings_resp.json()["results"]
    assert len(findings) == 1
    assert findings[0]["owner_name"] == "Alice Zhang"
    assert findings[0]["owner_email"] == "alice@example.com"
    assert findings[0]["owner"] == "Alice Zhang"

    stats_resp = await client.get("/api/webhook/review-findings/stats/")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert any(item["name"] == "Alice Zhang" for item in stats["by_owner"])


@pytest.mark.asyncio
async def test_findings_support_problematic_code_alias(client, db_session) -> None:
    review = MergeRequestReview(
        project_id=7003,
        project_name="demo-project-3",
        merge_request_iid=33,
        merge_request_title="feat: support problematic_code",
        source_branch="feature/problematic-code",
        target_branch="main",
        author_name="Charlie",
        author_email="charlie@example.com",
        review_content="structured review",
        status="completed",
        review_issues=[
            {
                "severity": "high",
                "category": "bug",
                "file": "src/core.py",
                "line": 18,
                "description": "possible key error",
                "suggestion": "guard the key access",
                "problematic_code": "return payload['meta']['id']",
            }
        ],
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)

    findings_resp = await client.get(f"/api/webhook/reviews/{review.id}/findings/")
    assert findings_resp.status_code == 200
    findings = findings_resp.json()["results"]
    assert len(findings) == 1
    assert findings[0]["code_snippet"] == "return payload['meta']['id']"
