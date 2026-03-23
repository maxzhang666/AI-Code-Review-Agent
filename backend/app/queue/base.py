from __future__ import annotations

from abc import ABC, abstractmethod

from app.queue.types import TaskPayload, TaskResult, TaskStatus


class TaskQueue(ABC):
    @abstractmethod
    async def enqueue(self, payload: TaskPayload) -> str:
        raise NotImplementedError

    @abstractmethod
    async def dequeue(self) -> tuple[str, TaskPayload] | None:
        raise NotImplementedError

    @abstractmethod
    async def ack(self, task_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def nack(self, task_id: str, error: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_status(self, task_id: str) -> TaskStatus:
        raise NotImplementedError

    @abstractmethod
    async def list_tasks(self, status: TaskStatus | None = None, limit: int = 100) -> list[TaskResult]:
        raise NotImplementedError

    @abstractmethod
    async def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> None:
        raise NotImplementedError
