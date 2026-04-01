from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.models import TaskEvent, TaskObservation, WeeklySnapshotSchedulerLog


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@pytest.mark.asyncio
async def test_tasks_summary_route_returns_aggregations(client, db_session) -> None:
    now = _now()
    t1 = str(uuid4())
    t2 = str(uuid4())
    db_session.add_all([
        TaskObservation(
            task_id=t1,
            task_type="generate_weekly",
            status="completed",
            priority=1,
            retry_count=0,
            max_retries=1,
            payload={"scope": "team"},
            result={"ok": True},
            created_at=now,
            updated_at=now,
            started_at=now,
            completed_at=now,
        ),
        TaskObservation(
            task_id=t2,
            task_type="generate_weekly",
            status="failed",
            priority=1,
            retry_count=1,
            max_retries=1,
            payload={"scope": "team"},
            error_message="boom",
            created_at=now,
            updated_at=now,
            started_at=now,
            completed_at=now,
        ),
    ])
    await db_session.commit()

    response = await client.get("/api/system/tasks/summary")
    assert response.status_code == 200
    payload = response.json()

    assert payload["queue_backend"] == "memory"
    assert payload["is_persistent"] is False
    assert payload["observability_persistent"] is True
    assert payload["by_status"]["completed"] == 1
    assert payload["by_status"]["failed"] == 1
    assert payload["by_task_type"]["generate_weekly"] == 2


@pytest.mark.asyncio
async def test_tasks_list_supports_filters_and_pagination(client, db_session) -> None:
    now = _now()
    run_id_a = str(uuid4())
    run_id_b = str(uuid4())
    t1 = str(uuid4())
    t2 = str(uuid4())
    t3 = str(uuid4())
    db_session.add_all([
        TaskObservation(
            task_id=t1,
            run_id=run_id_a,
            task_type="a",
            status="pending",
            priority=1,
            retry_count=0,
            max_retries=1,
            payload={},
            created_at=now - timedelta(hours=3),
            updated_at=now - timedelta(hours=3),
        ),
        TaskObservation(
            task_id=t2,
            run_id=run_id_a,
            task_type="a",
            status="failed",
            priority=1,
            retry_count=1,
            max_retries=1,
            payload={},
            error_message="e2",
            created_at=now - timedelta(hours=2),
            updated_at=now - timedelta(hours=2),
        ),
        TaskObservation(
            task_id=t3,
            run_id=run_id_b,
            task_type="b",
            status="completed",
            priority=1,
            retry_count=0,
            max_retries=1,
            payload={},
            result={"ok": True},
            created_at=now - timedelta(hours=1),
            updated_at=now - timedelta(hours=1),
            started_at=now - timedelta(hours=1),
            completed_at=now - timedelta(hours=1) + timedelta(seconds=1),
        ),
    ])
    await db_session.commit()

    response = await client.get(
        "/api/system/tasks/",
        params={"status": "failed", "page": 1, "limit": 10},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 1
    assert len(payload["results"]) == 1
    assert payload["results"][0]["task_id"] == t2

    response_by_id = await client.get(
        "/api/system/tasks/",
        params={"task_id": t3},
    )
    assert response_by_id.status_code == 200
    payload_by_id = response_by_id.json()
    assert payload_by_id["count"] == 1
    assert payload_by_id["results"][0]["task_type"] == "b"
    assert payload_by_id["results"][0]["run_id"] == run_id_b

    response_by_run = await client.get(
        "/api/system/tasks/",
        params={"run_id": run_id_a},
    )
    assert response_by_run.status_code == 200
    payload_by_run = response_by_run.json()
    assert payload_by_run["count"] == 2
    assert {item["task_id"] for item in payload_by_run["results"]} == {t1, t2}


@pytest.mark.asyncio
async def test_task_detail_and_events_endpoints(client, db_session) -> None:
    now = _now()
    task_id = str(uuid4())
    run_id = str(uuid4())
    db_session.add(
        TaskObservation(
            task_id=task_id,
            run_id=run_id,
            task_type="generate_developer_weekly_snapshot",
            status="failed",
            priority=1,
            retry_count=1,
            max_retries=1,
            payload={"owner": "alex"},
            error_message="bad request",
            created_at=now - timedelta(minutes=2),
            started_at=now - timedelta(minutes=1, seconds=30),
            completed_at=now - timedelta(minutes=1),
            updated_at=now - timedelta(minutes=1),
        )
    )
    db_session.add_all([
        TaskEvent(
            task_id=task_id,
            run_id=run_id,
            event_type="started",
            status_after="processing",
            attempt_no=1,
            created_at=now - timedelta(minutes=1, seconds=30),
        ),
        TaskEvent(
            task_id=task_id,
            run_id=run_id,
            event_type="failed",
            status_after="failed",
            attempt_no=1,
            message="bad request",
            created_at=now - timedelta(minutes=1),
        ),
    ])
    await db_session.commit()

    detail_response = await client.get(f"/api/system/tasks/{task_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["task_id"] == task_id
    assert detail["run_id"] == run_id
    assert detail["status"] == "failed"
    assert detail["duration_ms"] is not None
    assert len(detail["events"]) == 2
    assert {event["event_type"] for event in detail["events"]} == {"started", "failed"}

    events_response = await client.get(f"/api/system/tasks/{task_id}/events", params={"limit": 1})
    assert events_response.status_code == 200
    events = events_response.json()
    assert len(events) == 1
    assert events[0]["event_type"] in {"started", "failed"}
    assert events[0]["run_id"] == run_id


@pytest.mark.asyncio
async def test_tasks_summary_route_not_captured_by_task_id_route(client) -> None:
    response = await client.get("/api/system/tasks/summary")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tasks_endpoints_return_empty_payload_when_no_data(client) -> None:
    summary_response = await client.get("/api/system/tasks/summary")
    assert summary_response.status_code == 200
    summary_payload = summary_response.json()
    assert summary_payload["by_status"] == {}
    assert summary_payload["by_task_type"] == {}

    list_response = await client.get("/api/system/tasks/")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["count"] == 0
    assert list_payload["results"] == []


@pytest.mark.asyncio
async def test_tasks_list_rejects_invalid_paging_params(client) -> None:
    response_page = await client.get("/api/system/tasks/", params={"page": 0})
    assert response_page.status_code == 400
    assert response_page.json()["message"] == "page must be >= 1."

    response_limit = await client.get("/api/system/tasks/", params={"limit": 201})
    assert response_limit.status_code == 400
    assert response_limit.json()["message"] == "limit must be between 1 and 200."


@pytest.mark.asyncio
async def test_task_detail_and_events_validate_uuid_and_not_found(client) -> None:
    invalid_detail = await client.get("/api/system/tasks/not-a-uuid")
    assert invalid_detail.status_code == 422
    assert invalid_detail.json()["message"] == "Validation error"

    invalid_events = await client.get("/api/system/tasks/not-a-uuid/events")
    assert invalid_events.status_code == 422
    assert invalid_events.json()["message"] == "Validation error"

    missing_task_id = str(uuid4())
    not_found_detail = await client.get(f"/api/system/tasks/{missing_task_id}")
    assert not_found_detail.status_code == 404
    assert not_found_detail.json()["message"] == "Task not found."

    not_found_events = await client.get(f"/api/system/tasks/{missing_task_id}/events")
    assert not_found_events.status_code == 404
    assert not_found_events.json()["message"] == "Task not found."


@pytest.mark.asyncio
async def test_task_events_rejects_invalid_limit(client, db_session) -> None:
    task_id = str(uuid4())
    now = _now()
    db_session.add(
        TaskObservation(
            task_id=task_id,
            task_type="test",
            status="pending",
            priority=1,
            retry_count=0,
            max_retries=1,
            payload={},
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.commit()

    response = await client.get(
        f"/api/system/tasks/{task_id}/events",
        params={"limit": 1001},
    )
    assert response.status_code == 400
    assert response.json()["message"] == "limit must be between 1 and 1000."


@pytest.mark.asyncio
async def test_weekly_scheduler_logs_endpoint_supports_filters(client, db_session) -> None:
    now = _now()
    db_session.add_all(
        [
            WeeklySnapshotSchedulerLog(
                status="skipped",
                reason="not_trigger_time",
                created_at=now - timedelta(minutes=2),
            ),
            WeeklySnapshotSchedulerLog(
                status="queued",
                run_id="run-abc",
                task_id=str(uuid4()),
                week_start=(now - timedelta(days=7)).date(),
                created_at=now - timedelta(minutes=1),
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/system/reports/developers/weekly/scheduler-logs", params={"limit": 10})
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 2
    assert len(payload["results"]) >= 2

    filtered = await client.get(
        "/api/system/reports/developers/weekly/scheduler-logs",
        params={"status": "queued", "run_id": "run-abc", "limit": 10},
    )
    assert filtered.status_code == 200
    filtered_payload = filtered.json()
    assert filtered_payload["count"] >= 1
    assert filtered_payload["results"][0]["status"] == "queued"
    assert filtered_payload["results"][0]["run_id"] == "run-abc"


@pytest.mark.asyncio
async def test_weekly_scheduler_logs_endpoint_supports_pagination(client, db_session) -> None:
    now = _now()
    db_session.add_all(
        [
            WeeklySnapshotSchedulerLog(
                status="skipped",
                reason="pagination_case",
                created_at=now - timedelta(minutes=3),
            ),
            WeeklySnapshotSchedulerLog(
                status="skipped",
                reason="pagination_case",
                created_at=now - timedelta(minutes=2),
            ),
            WeeklySnapshotSchedulerLog(
                status="skipped",
                reason="pagination_case",
                created_at=now - timedelta(minutes=1),
            ),
        ]
    )
    await db_session.commit()

    first_page = await client.get(
        "/api/system/reports/developers/weekly/scheduler-logs",
        params={"reason": "pagination_case", "page": 1, "limit": 2},
    )
    assert first_page.status_code == 200
    first_payload = first_page.json()
    assert first_payload["count"] == 3
    assert len(first_payload["results"]) == 2

    second_page = await client.get(
        "/api/system/reports/developers/weekly/scheduler-logs",
        params={"reason": "pagination_case", "page": 2, "limit": 2},
    )
    assert second_page.status_code == 200
    second_payload = second_page.json()
    assert second_payload["count"] == 3
    assert len(second_payload["results"]) == 1


@pytest.mark.asyncio
async def test_weekly_scheduler_logs_endpoint_rejects_invalid_page(client) -> None:
    response = await client.get(
        "/api/system/reports/developers/weekly/scheduler-logs",
        params={"page": 0, "limit": 10},
    )
    assert response.status_code == 400
    assert response.json()["message"] == "page must be >= 1."


@pytest.mark.asyncio
async def test_system_maintenance_cleanup_task_events_dry_run_and_execute(client, db_session) -> None:
    now = _now()
    db_session.add_all(
        [
            TaskEvent(
                task_id=str(uuid4()),
                event_type="enqueued",
                status_after="pending",
                attempt_no=0,
                created_at=now - timedelta(days=40),
            ),
            TaskEvent(
                task_id=str(uuid4()),
                event_type="enqueued",
                status_after="pending",
                attempt_no=0,
                created_at=now - timedelta(days=3),
            ),
        ]
    )
    await db_session.commit()

    dry_run = await client.post(
        "/api/system/maintenance/cleanup/task-events",
        json={"retention_days": 30, "dry_run": True},
    )
    assert dry_run.status_code == 200
    dry_payload = dry_run.json()
    assert dry_payload["resource"] == "task_events"
    assert dry_payload["stale_count"] == 1
    assert dry_payload["deleted_count"] == 0

    execute = await client.post(
        "/api/system/maintenance/cleanup/task-events",
        json={"retention_days": 30, "dry_run": False},
    )
    assert execute.status_code == 200
    exec_payload = execute.json()
    assert exec_payload["deleted_count"] == 1


@pytest.mark.asyncio
async def test_system_maintenance_cleanup_weekly_scheduler_logs_dry_run_and_execute(client, db_session) -> None:
    now = _now()
    db_session.add_all(
        [
            WeeklySnapshotSchedulerLog(
                status="skipped",
                reason="disabled",
                created_at=now - timedelta(days=100),
            ),
            WeeklySnapshotSchedulerLog(
                status="queued",
                run_id="run-keep",
                task_id=str(uuid4()),
                created_at=now - timedelta(days=5),
            ),
        ]
    )
    await db_session.commit()

    dry_run = await client.post(
        "/api/system/maintenance/cleanup/weekly-scheduler-logs",
        json={"retention_days": 90, "dry_run": True},
    )
    assert dry_run.status_code == 200
    dry_payload = dry_run.json()
    assert dry_payload["resource"] == "weekly_snapshot_scheduler_logs"
    assert dry_payload["stale_count"] == 1
    assert dry_payload["deleted_count"] == 0

    execute = await client.post(
        "/api/system/maintenance/cleanup/weekly-scheduler-logs",
        json={"retention_days": 90, "dry_run": False},
    )
    assert execute.status_code == 200
    exec_payload = execute.json()
    assert exec_payload["deleted_count"] == 1


@pytest.mark.asyncio
async def test_system_maintenance_cleanup_rejects_invalid_retention_days(client) -> None:
    response = await client.post(
        "/api/system/maintenance/cleanup/task-events",
        json={"retention_days": 0, "dry_run": True},
    )
    assert response.status_code == 400
    assert response.json()["message"] == "retention_days must be between 1 and 3650."
