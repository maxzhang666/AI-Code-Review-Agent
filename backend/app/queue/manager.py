from __future__ import annotations

import asyncio
import inspect
from datetime import UTC, datetime
from typing import Any

from app.config import TaskQueueBackend, get_settings
from app.core.logging import get_logger
from app.database import get_session_factory
from app.models import TaskEvent, TaskObservation
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
        self._session_factory = get_session_factory()
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
        task_id = await self._queue.enqueue(payload)
        await self._observe_enqueued(task_id, payload)
        return task_id

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
        attempt_no = await self._observe_started(task_id, payload)
        handler = get_handler(payload.task_type)
        if handler is None:
            error = f"No handler for task_type={payload.task_type}"
            await self._queue.nack(task_id, error)
            await self._observe_after_nack(task_id, payload, error, attempt_no_hint=attempt_no)
            return
        try:
            result = handler(payload.data)
            if inspect.isawaitable(result):
                result = await result
            await self._queue.ack(task_id)
            await self._observe_completed(task_id, payload, result, attempt_no_hint=attempt_no)
            self._logger.info("queue_task_completed", task_id=task_id, task_type=payload.task_type)
        except Exception as exc:
            error = str(exc)
            await self._queue.nack(task_id, error)
            await self._observe_after_nack(task_id, payload, error, attempt_no_hint=attempt_no)
            self._logger.log_error_with_context("queue_task_failed", error=exc, task_id=task_id)

    def _utc_now(self) -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    def _normalize_result(self, value: Any) -> dict[str, Any] | None:
        if value is None:
            return None
        if isinstance(value, dict):
            return value
        if isinstance(value, (list, tuple, set)):
            return {"items": list(value)}
        if isinstance(value, (str, int, float, bool)):
            return {"value": value}
        return {"value": str(value)}

    def _extract_run_id(self, payload: TaskPayload) -> str | None:
        raw = payload.data.get("run_id") if isinstance(payload.data, dict) else None
        text = str(raw or "").strip()
        return text or None

    async def _observe_enqueued(self, task_id: str, payload: TaskPayload) -> None:
        try:
            now = self._utc_now()
            run_id = self._extract_run_id(payload)
            async with self._session_factory() as session:
                observation = await session.get(TaskObservation, task_id)
                if observation is None:
                    observation = TaskObservation(
                        task_id=task_id,
                        run_id=run_id,
                        task_type=payload.task_type,
                        status=TaskStatus.pending.value,
                        priority=int(payload.priority),
                        retry_count=0,
                        max_retries=payload.max_retries,
                        payload=payload.data,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(observation)
                else:
                    observation.run_id = run_id or observation.run_id
                    observation.task_type = payload.task_type
                    observation.status = TaskStatus.pending.value
                    observation.priority = int(payload.priority)
                    observation.max_retries = payload.max_retries
                    observation.payload = payload.data
                    observation.updated_at = now

                session.add(
                    TaskEvent(
                        task_id=task_id,
                        run_id=run_id,
                        event_type="enqueued",
                        status_after=TaskStatus.pending.value,
                        attempt_no=0,
                        event_payload={"task_type": payload.task_type, "priority": int(payload.priority)},
                        created_at=now,
                    )
                )
                await session.commit()
        except Exception as exc:
            self._logger.log_error_with_context(
                "task_observe_enqueued_failed",
                error=exc,
                task_id=task_id,
                task_type=payload.task_type,
            )

    async def _observe_started(self, task_id: str, payload: TaskPayload) -> int:
        try:
            now = self._utc_now()
            run_id = self._extract_run_id(payload)
            async with self._session_factory() as session:
                observation = await session.get(TaskObservation, task_id)
                if observation is None:
                    observation = TaskObservation(
                        task_id=task_id,
                        run_id=run_id,
                        task_type=payload.task_type,
                        status=TaskStatus.pending.value,
                        priority=int(payload.priority),
                        retry_count=0,
                        max_retries=payload.max_retries,
                        payload=payload.data,
                        created_at=now,
                        updated_at=now,
                    )
                    session.add(observation)

                attempt_no = int(observation.retry_count) + 1
                observation.run_id = run_id or observation.run_id
                observation.status = TaskStatus.processing.value
                if observation.started_at is None:
                    observation.started_at = now
                observation.updated_at = now

                session.add(
                    TaskEvent(
                        task_id=task_id,
                        run_id=run_id or observation.run_id,
                        event_type="started",
                        status_after=TaskStatus.processing.value,
                        attempt_no=attempt_no,
                        created_at=now,
                    )
                )
                await session.commit()
                return attempt_no
        except Exception as exc:
            self._logger.log_error_with_context(
                "task_observe_started_failed",
                error=exc,
                task_id=task_id,
                task_type=payload.task_type,
            )
        return 1

    async def _observe_completed(
        self,
        task_id: str,
        payload: TaskPayload,
        handler_result: Any,
        attempt_no_hint: int | None = None,
    ) -> None:
        try:
            now = self._utc_now()
            run_id = self._extract_run_id(payload)
            async with self._session_factory() as session:
                observation = await session.get(TaskObservation, task_id)
                if observation is None:
                    observation = TaskObservation(
                        task_id=task_id,
                        run_id=run_id,
                        task_type=payload.task_type,
                        status=TaskStatus.completed.value,
                        priority=int(payload.priority),
                        retry_count=0,
                        max_retries=payload.max_retries,
                        payload=payload.data,
                        created_at=now,
                        started_at=now,
                        updated_at=now,
                    )
                    session.add(observation)

                attempt_no = max(int(attempt_no_hint or (int(observation.retry_count) + 1)), 1)
                observation.run_id = run_id or observation.run_id
                observation.task_type = payload.task_type
                observation.status = TaskStatus.completed.value
                observation.priority = int(payload.priority)
                observation.max_retries = payload.max_retries
                observation.payload = payload.data
                observation.result = self._normalize_result(handler_result)
                observation.error_message = None
                if observation.started_at is None:
                    observation.started_at = now
                observation.completed_at = now
                observation.updated_at = now

                session.add(
                    TaskEvent(
                        task_id=task_id,
                        run_id=run_id or observation.run_id,
                        event_type="completed",
                        status_after=TaskStatus.completed.value,
                        attempt_no=attempt_no,
                        created_at=now,
                    )
                )
                await session.commit()
        except Exception as exc:
            self._logger.log_error_with_context(
                "task_observe_completed_failed",
                error=exc,
                task_id=task_id,
                task_type=payload.task_type,
            )

    async def _observe_after_nack(
        self,
        task_id: str,
        payload: TaskPayload,
        error: str,
        attempt_no_hint: int | None = None,
    ) -> None:
        try:
            now = self._utc_now()
            run_id = self._extract_run_id(payload)
            status_after = (await self._queue.get_status(task_id)).value
            if status_after not in {TaskStatus.pending.value, TaskStatus.retrying.value, TaskStatus.failed.value}:
                status_after = TaskStatus.failed.value

            event_type = "retry_scheduled" if status_after in {
                TaskStatus.pending.value,
                TaskStatus.retrying.value,
            } else "failed"

            async with self._session_factory() as session:
                observation = await session.get(TaskObservation, task_id)
                if observation is None:
                    observation = TaskObservation(
                        task_id=task_id,
                        run_id=run_id,
                        task_type=payload.task_type,
                        status=status_after,
                        priority=int(payload.priority),
                        retry_count=0,
                        max_retries=payload.max_retries,
                        payload=payload.data,
                        created_at=now,
                        started_at=now,
                        updated_at=now,
                    )
                    session.add(observation)

                attempt_no = max(int(attempt_no_hint or (int(observation.retry_count) + 1)), 1)
                observation.run_id = run_id or observation.run_id
                observation.task_type = payload.task_type
                observation.status = status_after
                observation.priority = int(payload.priority)
                observation.max_retries = payload.max_retries
                observation.payload = payload.data
                observation.retry_count = max(int(observation.retry_count), attempt_no)
                observation.error_message = error
                if observation.started_at is None:
                    observation.started_at = now
                if status_after == TaskStatus.failed.value:
                    observation.completed_at = now
                observation.updated_at = now

                session.add(
                    TaskEvent(
                        task_id=task_id,
                        run_id=run_id or observation.run_id,
                        event_type=event_type,
                        status_after=status_after,
                        attempt_no=attempt_no,
                        message=error,
                        event_payload={"error": error},
                        created_at=now,
                    )
                )
                await session.commit()
        except Exception as exc:
            self._logger.log_error_with_context(
                "task_observe_nack_failed",
                error=exc,
                task_id=task_id,
                task_type=payload.task_type,
            )
