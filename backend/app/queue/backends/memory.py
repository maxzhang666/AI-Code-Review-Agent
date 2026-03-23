from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.queue.base import TaskQueue
from app.queue.types import TaskPayload, TaskResult, TaskStatus


@dataclass
class _TaskState:
    payload: TaskPayload
    status: TaskStatus = TaskStatus.pending
    result: dict[str, Any] | None = None
    error: str | None = None
    retry_count: int = 0
    max_retries: int = 3


class MemoryQueue(TaskQueue):
    def __init__(self) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._tasks: dict[str, _TaskState] = {}
        self._running = False

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def enqueue(self, payload: TaskPayload) -> str:
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = _TaskState(payload=payload, max_retries=payload.max_retries)
        await self._queue.put(task_id)
        return task_id

    async def dequeue(self) -> tuple[str, TaskPayload] | None:
        if not self._running:
            return None
        try:
            task_id = self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None
        state = self._tasks.get(task_id)
        if state is None:
            return None
        state.status = TaskStatus.processing
        return task_id, state.payload

    async def ack(self, task_id: str) -> None:
        state = self._tasks.get(task_id)
        if state:
            state.status = TaskStatus.completed

    async def nack(self, task_id: str, error: str) -> None:
        state = self._tasks.get(task_id)
        if state is None:
            return
        state.retry_count += 1
        state.error = error
        if state.retry_count <= state.max_retries:
            state.status = TaskStatus.pending
            await self._queue.put(task_id)
        else:
            state.status = TaskStatus.failed

    async def get_status(self, task_id: str) -> TaskStatus:
        state = self._tasks.get(task_id)
        return state.status if state else TaskStatus.failed

    async def list_tasks(self, status: TaskStatus | None = None, limit: int = 100) -> list[TaskResult]:
        results: list[TaskResult] = []
        for tid, state in self._tasks.items():
            if status is not None and state.status != status:
                continue
            results.append(TaskResult(task_id=tid, status=state.status, result=state.result, error=state.error))
            if len(results) >= limit:
                break
        return results
