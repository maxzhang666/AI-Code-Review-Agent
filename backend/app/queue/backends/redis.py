from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import redis.asyncio as redis_asyncio

from app.queue.base import TaskQueue
from app.queue.types import TaskPayload, TaskPriority, TaskResult, TaskStatus


class RedisQueue(TaskQueue):
    def __init__(self, redis_url: str, queue_key: str = "task_queue:pending", meta_prefix: str = "task_queue:task:") -> None:
        self._redis_url = redis_url
        self._queue_key = queue_key
        self._meta_prefix = meta_prefix
        self._redis: redis_asyncio.Redis | None = None
        self._running = False

    async def start(self) -> None:
        self._redis = redis_asyncio.from_url(self._redis_url, encoding="utf-8", decode_responses=True)
        await self._redis.ping()
        self._running = True

    async def stop(self) -> None:
        self._running = False
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    def _client(self) -> redis_asyncio.Redis:
        if self._redis is None:
            raise RuntimeError("Redis queue not started.")
        return self._redis

    def _key(self, task_id: str) -> str:
        return f"{self._meta_prefix}{task_id}"

    async def enqueue(self, payload: TaskPayload) -> str:
        r = self._client()
        task_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        await r.hset(self._key(task_id), mapping={
            "task_type": payload.task_type,
            "data": json.dumps(payload.data, ensure_ascii=False),
            "priority": str(int(payload.priority)),
            "status": TaskStatus.pending.value,
            "retry_count": "0",
            "max_retries": str(payload.max_retries),
            "error_message": "",
            "result": "",
            "created_at": now,
            "updated_at": now,
        })
        await r.lpush(self._queue_key, task_id)
        return task_id

    async def dequeue(self) -> tuple[str, TaskPayload] | None:
        if not self._running:
            return None
        r = self._client()
        popped = await r.brpop(self._queue_key, timeout=1)
        if not popped:
            return None
        task_id = str(popped[1])
        meta = await r.hgetall(self._key(task_id))
        if not meta:
            return None
        await r.hset(self._key(task_id), mapping={
            "status": TaskStatus.processing.value,
            "updated_at": datetime.utcnow().isoformat(),
        })
        data = self._json(meta.get("data"))
        return task_id, TaskPayload(
            task_type=meta.get("task_type", ""),
            data=data if isinstance(data, dict) else {},
            priority=self._priority(meta.get("priority")),
            max_retries=int(meta.get("max_retries", "3")),
        )

    async def ack(self, task_id: str) -> None:
        await self._client().hset(self._key(task_id), mapping={
            "status": TaskStatus.completed.value,
            "updated_at": datetime.utcnow().isoformat(),
        })

    async def nack(self, task_id: str, error: str) -> None:
        r = self._client()
        meta = await r.hgetall(self._key(task_id))
        if not meta:
            return
        retry = int(meta.get("retry_count", "0")) + 1
        max_r = int(meta.get("max_retries", "3"))
        if retry <= max_r:
            await r.hset(self._key(task_id), mapping={
                "status": TaskStatus.pending.value, "retry_count": str(retry),
                "error_message": error, "updated_at": datetime.utcnow().isoformat(),
            })
            await r.lpush(self._queue_key, task_id)
        else:
            await r.hset(self._key(task_id), mapping={
                "status": TaskStatus.failed.value, "retry_count": str(retry),
                "error_message": error, "updated_at": datetime.utcnow().isoformat(),
            })

    async def get_status(self, task_id: str) -> TaskStatus:
        raw = await self._client().hget(self._key(task_id), "status")
        return self._status(raw)

    async def list_tasks(self, status: TaskStatus | None = None, limit: int = 100) -> list[TaskResult]:
        r = self._client()
        results: list[TaskResult] = []
        async for key in r.scan_iter(match=f"{self._meta_prefix}*"):
            meta = await r.hgetall(str(key))
            if not meta:
                continue
            ts = self._status(meta.get("status"))
            if status is not None and ts != status:
                continue
            res = self._json(meta.get("result"))
            results.append(TaskResult(
                task_id=str(key).replace(self._meta_prefix, "", 1),
                status=ts, result=res if isinstance(res, dict) else None,
                error=meta.get("error_message") or None,
            ))
            if len(results) >= limit:
                break
        return results

    def _json(self, raw: str | None) -> Any:
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def _priority(self, raw: str | None) -> TaskPriority:
        try:
            return TaskPriority(int(raw or 1))
        except ValueError:
            return TaskPriority.normal

    def _status(self, raw: str | None) -> TaskStatus:
        try:
            return TaskStatus(raw or "failed")
        except ValueError:
            return TaskStatus.failed
