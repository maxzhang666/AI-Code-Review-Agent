from __future__ import annotations

import time
from uuid import uuid4

import pytest

from app.queue.backends.memory import MemoryQueue
from app.queue.manager import QueueManager
from app.queue.types import TaskPayload


def _build_blob(size_kb: int, fill: str) -> str:
    return fill * (size_kb * 1024)


@pytest.mark.asyncio
async def test_task_observability_large_payload_query_baseline(
    test_app,  # noqa: ARG001
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Baseline scenario (V1): payload/result each 256KB, no truncation.
    payload_blob = _build_blob(256, "p")
    result_blob = _build_blob(256, "r")

    queue = MemoryQueue()
    await queue.start()
    manager = QueueManager(queue=queue)

    def _handler(_data: dict) -> dict:
        return {
            "result_blob": result_blob,
            "meta": {"ok": True},
        }

    monkeypatch.setattr("app.queue.manager.get_handler", lambda _task_type: _handler)

    payload = TaskPayload(
        task_type=f"large_payload_{uuid4()}",
        data={"payload_blob": payload_blob, "meta": {"source": "baseline"}},
        max_retries=0,
    )

    try:
        write_start = time.perf_counter()
        task_id = await manager.enqueue(payload)
        dequeued = await queue.dequeue()
        assert dequeued is not None
        await manager._process(dequeued[0], dequeued[1])
        write_elapsed = time.perf_counter() - write_start

        list_start = time.perf_counter()
        list_response = await client.get("/api/system/tasks/", params={"task_id": task_id})
        list_elapsed = time.perf_counter() - list_start
        assert list_response.status_code == 200

        detail_start = time.perf_counter()
        detail_response = await client.get(f"/api/system/tasks/{task_id}")
        detail_elapsed = time.perf_counter() - detail_start
        assert detail_response.status_code == 200
        detail_payload = detail_response.json()

        events_start = time.perf_counter()
        events_response = await client.get(f"/api/system/tasks/{task_id}/events")
        events_elapsed = time.perf_counter() - events_start
        assert events_response.status_code == 200

        assert detail_payload["payload"]["payload_blob"] == payload_blob
        assert detail_payload["result"]["result_blob"] == result_blob
        assert len(detail_payload["events"]) >= 3

        # Baseline gates: keep loose, only catch order-of-magnitude regressions.
        assert write_elapsed < 5.0
        assert list_elapsed < 2.0
        assert detail_elapsed < 2.0
        assert events_elapsed < 2.0
    finally:
        await queue.stop()
