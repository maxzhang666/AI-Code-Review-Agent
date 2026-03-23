from __future__ import annotations

from datetime import datetime as real_datetime

import pytest


@pytest.mark.asyncio
async def test_dashboard_recent_activity_time_uses_utc_baseline(
    client,
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.api import reviews as reviews_api
    from app.models import MergeRequestReview

    class FakeDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ARG003
            return cls(2026, 1, 1, 8, 30, 0)

        @classmethod
        def utcnow(cls):
            return cls(2026, 1, 1, 0, 30, 0)

    monkeypatch.setattr(reviews_api, "datetime", FakeDateTime)

    review = MergeRequestReview(
        project_id=1,
        project_name="demo",
        merge_request_iid=101,
        merge_request_title="Fix bug",
        source_branch="feature/fix",
        target_branch="main",
        author_name="dev",
        author_email="dev@example.com",
        status="completed",
        created_at=real_datetime(2026, 1, 1, 0, 0, 0),
    )
    db_session.add(review)
    await db_session.commit()

    response = await client.get("/api/webhook/dashboard/charts/?days=7")
    assert response.status_code == 200
    payload = response.json()
    assert payload["recent_activities"][0]["time"] == "30 分钟前"


@pytest.mark.asyncio
async def test_dashboard_recent_activity_includes_review_id_for_detail_navigation(
    client,
    db_session,
) -> None:
    from app.models import MergeRequestReview

    review = MergeRequestReview(
        project_id=2,
        project_name="demo-2",
        merge_request_iid=102,
        merge_request_title="Add feature",
        source_branch="feature/new",
        target_branch="main",
        author_name="dev2",
        author_email="dev2@example.com",
        status="completed",
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)

    response = await client.get("/api/webhook/dashboard/charts/?days=7")
    assert response.status_code == 200
    payload = response.json()
    assert payload["recent_activities"][0]["review_id"] == review.id
