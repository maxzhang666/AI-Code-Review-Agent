from __future__ import annotations

import asyncio
import inspect

from app.config import TaskQueueBackend, get_settings
from app.core.logging import get_logger
from app.queue.backends.database import DatabaseQueue
from app.queue.backends.memory import MemoryQueue
from app.queue.backends.redis import RedisQueue
from app.queue.base import TaskQueue
from app.queue.tasks import get_handler
from app.queue.types import TaskPayload, TaskResult, TaskStatus


class QueueManager:
    def __init__(self, queue: TaskQueue | None = None) -> None:
        self._logger = get_logger(__name__)
        self._queue = queue or self._create_queue()
        self._worker_task: asyncio.Task | None = None
        self._running = False

    def _create_queue(self) -> TaskQueue:
        settings = get_settings()
        if settings.TASK_QUEUE_BACKEND == TaskQueueBackend.redis:
            return RedisQueue(settings.REDIS_URL)
        if settings.TASK_QUEUE_BACKEND == TaskQueueBackend.database:
            return DatabaseQueue()
        return MemoryQueue()

    async def start_worker(self) -> None:
        if self._running:
            return
        await self._queue.start()
        self._running = True
        self._worker_task = asyncio.create_task(self._loop(), name="task-queue-worker")
        self._logger.info("queue_worker_started")

    async def stop_worker(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        await self._queue.stop()
        self._logger.info("queue_worker_stopped")

    async def enqueue(self, payload: TaskPayload) -> str:
        return await self._queue.enqueue(payload)

    async def get_status(self, task_id: str) -> TaskStatus:
        return await self._queue.get_status(task_id)

    async def list_tasks(self, status: TaskStatus | None = None, limit: int = 100) -> list[TaskResult]:
        return await self._queue.list_tasks(status=status, limit=limit)

    async def _loop(self) -> None:
        while self._running:
            try:
                item = await self._queue.dequeue()
                if item is None:
                    await asyncio.sleep(0.1)
                    continue
                task_id, payload = item
                await self._process(task_id, payload)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._logger.log_error_with_context("queue_worker_error", error=exc)
                await asyncio.sleep(1.0)

    async def _process(self, task_id: str, payload: TaskPayload) -> None:
        handler = get_handler(payload.task_type)
        if handler is None:
            await self._queue.nack(task_id, f"No handler for task_type={payload.task_type}")
            return
        try:
            result = handler(payload.data)
            if inspect.isawaitable(result):
                await result
            await self._queue.ack(task_id)
            self._logger.info("queue_task_completed", task_id=task_id, task_type=payload.task_type)
        except Exception as exc:
            await self._queue.nack(task_id, str(exc))
            self._logger.log_error_with_context("queue_task_failed", error=exc, task_id=task_id)
