from __future__ import annotations

from datetime import datetime

import pytest

from app.models import MergeRequestReview, Project, WebhookLog


@pytest.mark.asyncio
async def test_list_projects_returns_enriched_project_card_stats(client, db_session) -> None:
    project = Project(
        project_id=9101,
        project_name="stats-demo",
        project_path="group/stats-demo",
        project_url="https://gitlab.example.com/group/stats-demo.git",
        namespace="group",
        review_enabled=True,
        gitlab_data={
            "description": "demo description from gitlab",
            "last_activity_at": "2026-03-19T10:00:00Z",
        },
    )
    empty_project = Project(
        project_id=9102,
        project_name="empty-demo",
        project_path="group/empty-demo",
        project_url="https://gitlab.example.com/group/empty-demo.git",
        namespace="group",
        review_enabled=False,
        gitlab_data={"description": "empty project"},
    )
    db_session.add_all([project, empty_project])
    await db_session.flush()

    db_session.add_all(
        [
            WebhookLog(
                event_type="Push Hook",
                project_id=project.project_id,
                project_name=project.project_name,
                merge_request_iid=None,
                user_name="Alice",
                user_email="alice@example.com",
                source_branch="feature/a",
                target_branch="main",
                payload={},
                request_headers={},
                request_body_raw="{}",
            ),
            WebhookLog(
                event_type="Push Hook",
                project_id=project.project_id,
                project_name=project.project_name,
                merge_request_iid=None,
                user_name="Bob",
                user_email="bob@example.com",
                source_branch="feature/b",
                target_branch="main",
                payload={},
                request_headers={},
                request_body_raw="{}",
            ),
            WebhookLog(
                event_type="Merge Request Hook",
                project_id=project.project_id,
                project_name=project.project_name,
                merge_request_iid=101,
                user_name="Alice",
                user_email="alice@example.com",
                source_branch="feature/a",
                target_branch="main",
                payload={},
                request_headers={},
                request_body_raw="{}",
            ),
            WebhookLog(
                event_type="Merge Request Hook",
                project_id=project.project_id,
                project_name=project.project_name,
                merge_request_iid=102,
                user_name="Bob",
                user_email="bob@example.com",
                source_branch="feature/b",
                target_branch="main",
                payload={},
                request_headers={},
                request_body_raw="{}",
            ),
            WebhookLog(
                event_type="Merge Request Hook",
                project_id=project.project_id,
                project_name=project.project_name,
                merge_request_iid=102,
                user_name="unknown",
                user_email="unknown@example.com",
                source_branch="feature/c",
                target_branch="main",
                payload={},
                request_headers={},
                request_body_raw="{}",
            ),
        ]
    )
    db_session.add(
        MergeRequestReview(
            project_id=project.project_id,
            project_name=project.project_name,
            merge_request_iid=102,
            merge_request_title="feat: card stats",
            source_branch="feature/b",
            target_branch="main",
            author_name="Bob",
            author_email="bob@example.com",
            review_content="ok",
            status="completed",
            created_at=datetime.now(),
        )
    )
    await db_session.commit()

    response = await client.get("/api/webhook/projects/")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("count") == 2
    results = payload.get("results") or []
    result_by_id = {int(item.get("project_id")): item for item in results}

    stats_project = result_by_id.get(project.project_id)
    assert stats_project is not None
    assert stats_project.get("description") == "demo description from gitlab"
    assert stats_project.get("commits_count") == 2
    assert stats_project.get("mr_count") == 2
    assert stats_project.get("members_count") == 2
    assert stats_project.get("weekly_reviews") == 1
    assert stats_project.get("recent_events_count") == 5
    assert isinstance(stats_project.get("last_activity"), str)
    assert stats_project.get("last_activity")

    empty_stats_project = result_by_id.get(empty_project.project_id)
    assert empty_stats_project is not None
    assert empty_stats_project.get("commits_count") == 0
    assert empty_stats_project.get("mr_count") == 0
    assert empty_stats_project.get("members_count") == 0
    assert empty_stats_project.get("weekly_reviews") == 0
    assert empty_stats_project.get("recent_events_count") == 0
