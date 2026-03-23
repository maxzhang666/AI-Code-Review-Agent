from __future__ import annotations

import pytest

from app.queue.backends.memory import MemoryQueue
from app.queue.types import TaskPayload, TaskStatus


@pytest.mark.asyncio
async def test_memory_queue_enqueue_dequeue_ack_flow() -> None:
    queue = MemoryQueue()
    await queue.start()

    task_id = await queue.enqueue(TaskPayload(task_type="review_mr", data={"x": 1}))
    item = await queue.dequeue()
    assert item is not None
    dequeued_id, payload = item
    assert dequeued_id == task_id
    assert payload.task_type == "review_mr"

    await queue.ack(task_id)
    assert await queue.get_status(task_id) == TaskStatus.completed
    await queue.stop()


@pytest.mark.asyncio
async def test_memory_queue_nack_retry_then_fail() -> None:
    queue = MemoryQueue()
    await queue.start()

    task_id = await queue.enqueue(TaskPayload(task_type="review_mr", data={"y": 2}, max_retries=1))
    assert await queue.dequeue() is not None

    await queue.nack(task_id, "temporary-error")
    assert await queue.get_status(task_id) == TaskStatus.pending
    retried = await queue.dequeue()
    assert retried is not None and retried[0] == task_id

    await queue.nack(task_id, "permanent-error")
    assert await queue.get_status(task_id) == TaskStatus.failed
    await queue.stop()
