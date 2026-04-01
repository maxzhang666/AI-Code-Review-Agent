from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.database import get_session_factory
from app.models import TaskEvent, TaskObservation
from app.queue.backends.memory import MemoryQueue
from app.queue.manager import QueueManager
from app.queue.types import TaskPayload


async def _load_task_data(task_id: str) -> tuple[TaskObservation | None, list[TaskEvent]]:
    async with get_session_factory()() as session:
        observation = await session.get(TaskObservation, task_id)
        events = (
            await session.execute(
                select(TaskEvent)
                .where(TaskEvent.task_id == task_id)
                .order_by(TaskEvent.id.asc())
            )
        ).scalars().all()
    return observation, list(events)


@pytest.mark.asyncio
async def test_queue_manager_observes_success_lifecycle(
    test_app,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = MemoryQueue()
    await queue.start()
    manager = QueueManager(queue=queue)

    def _ok_handler(data: dict[str, Any]) -> dict[str, Any]:
        return {"received": data.get("name", "")}

    monkeypatch.setattr("app.queue.manager.get_handler", lambda _task_type: _ok_handler)

    run_id = str(uuid4())
    payload = TaskPayload(task_type="unit_success", data={"name": "demo", "run_id": run_id}, max_retries=1)
    task_id = await manager.enqueue(payload)

    item = await queue.dequeue()
    assert item is not None
    dequeued_id, dequeued_payload = item
    assert dequeued_id == task_id
    await manager._process(task_id, dequeued_payload)

    observation, events = await _load_task_data(task_id)
    assert observation is not None
    assert observation.status == "completed"
    assert observation.run_id == run_id
    assert observation.retry_count == 0
    assert observation.result == {"received": "demo"}
    assert [event.event_type for event in events] == ["enqueued", "started", "completed"]
    assert [event.attempt_no for event in events] == [0, 1, 1]
    assert {event.run_id for event in events} == {run_id}

    await queue.stop()


@pytest.mark.asyncio
async def test_queue_manager_observes_retry_then_complete(
    test_app,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    queue = MemoryQueue()
    await queue.start()
    manager = QueueManager(queue=queue)

    calls = {"count": 0}

    def _handler_with_one_retry(_data: dict[str, Any]) -> dict[str, Any]:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("temporary failure")
        return {"done": True}

    monkeypatch.setattr("app.queue.manager.get_handler", lambda _task_type: _handler_with_one_retry)

    run_id = str(uuid4())
    payload = TaskPayload(task_type=f"unit_retry_{uuid4()}", data={"x": 1, "run_id": run_id}, max_retries=1)
    task_id = await manager.enqueue(payload)

    first = await queue.dequeue()
    assert first is not None
    await manager._process(first[0], first[1])

    second = await queue.dequeue()
    assert second is not None
    await manager._process(second[0], second[1])

    observation, events = await _load_task_data(task_id)
    assert observation is not None
    assert observation.status == "completed"
    assert observation.run_id == run_id
    assert observation.retry_count == 1
    assert observation.error_message is None
    assert observation.result == {"done": True}
    assert [event.event_type for event in events] == [
        "enqueued",
        "started",
        "retry_scheduled",
        "started",
        "completed",
    ]
    assert [event.attempt_no for event in events] == [0, 1, 1, 2, 2]
    assert {event.run_id for event in events} == {run_id}

    await queue.stop()
