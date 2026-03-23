from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import select

from app.config import get_settings
from app.database import get_session_factory
from app.models import TaskRecord
from app.queue.base import TaskQueue
from app.queue.types import TaskPayload, TaskPriority, TaskResult, TaskStatus


class DatabaseQueue(TaskQueue):
    def __init__(self) -> None:
        self._settings = get_settings()
        self._session_factory = get_session_factory()
        self._running = False

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def enqueue(self, payload: TaskPayload) -> str:
        task_id = str(uuid.uuid4())
        record = TaskRecord(
            id=task_id, task_type=payload.task_type, payload=payload.data,
            status=TaskStatus.pending.value, priority=int(payload.priority),
            max_retries=payload.max_retries,
        )
        async with self._session_factory() as session:
            session.add(record)
            await session.commit()
        return task_id

    async def dequeue(self) -> tuple[str, TaskPayload] | None:
        if not self._running:
            return None
        if self._settings.is_sqlite:
            return await self._dequeue_sqlite()
        return await self._dequeue_postgres()

    async def _dequeue_sqlite(self) -> tuple[str, TaskPayload] | None:
        async with self._session_factory() as session:
            stmt = (
                select(TaskRecord)
                .where(TaskRecord.status == TaskStatus.pending.value)
                .order_by(TaskRecord.priority.desc(), TaskRecord.created_at.asc())
                .limit(1)
            )
            record = (await session.execute(stmt)).scalars().first()
            if record is None:
                await asyncio.sleep(2.0)
                return None
            # Atomic claim via status transition
            claim = (
                sa.update(TaskRecord)
                .where(TaskRecord.id == record.id, TaskRecord.status == TaskStatus.pending.value)
                .values(status=TaskStatus.processing.value, started_at=sa.func.now(), updated_at=sa.func.now())
            )
            result = await session.execute(claim)
            if result.rowcount != 1:
                await session.rollback()
                return None
            await session.commit()
            return record.id, self._to_payload(record)

    async def _dequeue_postgres(self) -> tuple[str, TaskPayload] | None:
        async with self._session_factory() as session:
            async with session.begin():
                stmt = (
                    select(TaskRecord)
                    .where(TaskRecord.status == TaskStatus.pending.value)
                    .order_by(TaskRecord.priority.desc(), TaskRecord.created_at.asc())
                    .with_for_update(skip_locked=True)
                    .limit(1)
                )
                record = (await session.execute(stmt)).scalars().first()
                if record is None:
                    return None
                record.status = TaskStatus.processing.value
                record.started_at = datetime.now()
                return record.id, self._to_payload(record)

    async def ack(self, task_id: str) -> None:
        async with self._session_factory() as session:
            await session.execute(
                sa.update(TaskRecord).where(TaskRecord.id == task_id)
                .values(status=TaskStatus.completed.value, completed_at=sa.func.now(), updated_at=sa.func.now())
            )
            await session.commit()

    async def nack(self, task_id: str, error: str) -> None:
        async with self._session_factory() as session:
            record = await session.get(TaskRecord, task_id)
            if record is None:
                return
            record.retry_count += 1
            record.error_message = error
            record.status = TaskStatus.pending.value if record.retry_count <= record.max_retries else TaskStatus.failed.value
            await session.commit()

    async def get_status(self, task_id: str) -> TaskStatus:
        async with self._session_factory() as session:
            raw = (await session.execute(select(TaskRecord.status).where(TaskRecord.id == task_id))).scalar_one_or_none()
            try:
                return TaskStatus(raw) if raw else TaskStatus.failed
            except ValueError:
                return TaskStatus.failed

    async def list_tasks(self, status: TaskStatus | None = None, limit: int = 100) -> list[TaskResult]:
        async with self._session_factory() as session:
            stmt = select(TaskRecord).order_by(TaskRecord.created_at.desc()).limit(limit)
            if status is not None:
                stmt = stmt.where(TaskRecord.status == status.value)
            records = (await session.execute(stmt)).scalars().all()
        return [
            TaskResult(task_id=r.id, status=TaskStatus(r.status), result=r.result, error=r.error_message)
            for r in records
        ]

    def _to_payload(self, record: TaskRecord) -> TaskPayload:
        try:
            priority = TaskPriority(record.priority)
        except ValueError:
            priority = TaskPriority.normal
        return TaskPayload(task_type=record.task_type, data=record.payload or {}, priority=priority, max_retries=record.max_retries)
