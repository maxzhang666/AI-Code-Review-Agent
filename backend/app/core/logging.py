from __future__ import annotations

import functools
import inspect
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

LOG_FORMAT = "%(asctime)s | %(levelname)-5s | %(name)s | %(message)s"

# Third-party loggers to suppress at WARNING level
_NOISY_LOGGERS = (
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "sqlalchemy.dialects",
    "sqlalchemy.orm",
    "httpx",
    "httpcore",
    "uvicorn.access",
    "watchfiles",
    "aiosqlite",
)


def configure_logging(
    log_level: str = "INFO",
    log_dir: str = "./logs",
    max_bytes: int = 2 * 1024 * 1024,
    backup_count: int = 10,
) -> None:
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    level = log_level.upper()
    root = logging.getLogger()
    root.setLevel(level)
    file_path = (Path(log_dir) / "app.log").resolve()

    fmt = logging.Formatter(LOG_FORMAT)

    has_console = any(getattr(handler, "_cr_handler_type", "") == "console" for handler in root.handlers)
    if not has_console:
        console = logging.StreamHandler()
        console.setFormatter(fmt)
        console._cr_handler_type = "console"  # type: ignore[attr-defined]
        root.addHandler(console)

    existing_file_handler: RotatingFileHandler | None = None
    for handler in root.handlers:
        if getattr(handler, "_cr_handler_type", "") == "file" and isinstance(handler, RotatingFileHandler):
            existing_file_handler = handler
            break

    needs_new_file_handler = existing_file_handler is None
    if existing_file_handler is not None:
        same_path = Path(existing_file_handler.baseFilename).resolve() == file_path
        same_config = (
            existing_file_handler.maxBytes == max_bytes
            and existing_file_handler.backupCount == backup_count
        )
        if not (same_path and same_config):
            root.removeHandler(existing_file_handler)
            existing_file_handler.close()
            needs_new_file_handler = True

    if needs_new_file_handler:
        fh = RotatingFileHandler(
            file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        fh.setFormatter(fmt)
        fh._cr_handler_type = "file"  # type: ignore[attr-defined]
        root.addHandler(fh)

    # Suppress noisy third-party loggers
    for name in _NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)


class StructuredLogger:
    def __init__(self, name: str, request_id: str | None = None):
        self.logger = logging.getLogger(name)
        self.request_id = request_id

    def _fmt(self, message: str, **kwargs: Any) -> str:
        out = f"[{self.request_id}] {message}" if self.request_id else message
        if kwargs:
            out += " | " + " | ".join(f"{k}={v}" for k, v in kwargs.items())
        return out

    # Base log methods
    def info(self, message: str, **kw: Any) -> None:
        self.logger.info(self._fmt(message, **kw))

    def warning(self, message: str, **kw: Any) -> None:
        self.logger.warning(self._fmt(message, **kw))

    def error(self, message: str, **kw: Any) -> None:
        self.logger.error(self._fmt(message, **kw))

    def debug(self, message: str, **kw: Any) -> None:
        self.logger.debug(self._fmt(message, **kw))

    # Domain-specific log methods
    def log_webhook_inbound(
        self, event_type: str, project_id: int, project_name: str, **kw: Any,
    ) -> None:
        self.info("webhook_inbound", event_type=event_type, project_id=project_id, project_name=project_name, **kw)

    def log_gitlab_interaction(
        self, action: str, project_id: int, mr_iid: int, success: bool, duration: float | None = None, **kw: Any,
    ) -> None:
        extra: dict[str, Any] = {"action": action, "project_id": project_id, "mr_iid": mr_iid, "success": success}
        if duration is not None:
            extra["duration"] = f"{duration:.2f}s"
        (self.info if success else self.error)("gitlab_interaction", **extra, **kw)

    def log_llm_call(
        self, provider: str, model: str, success: bool,
        duration: float | None = None, error: str | None = None, **kw: Any,
    ) -> None:
        extra: dict[str, Any] = {"provider": provider, "model": model, "success": success}
        if duration is not None:
            extra["duration"] = f"{duration:.2f}s"
        if error:
            extra["error"] = error
        (self.info if success else self.error)("llm_call", **extra, **kw)

    def log_notification_dispatch(
        self, total: int, success: int, failed: int, duration: float | None = None, **kw: Any,
    ) -> None:
        extra: dict[str, Any] = {"total": total, "success": success, "failed": failed}
        if duration is not None:
            extra["duration"] = f"{duration:.2f}s"
        self.info("notification_dispatch", **extra, **kw)

    def log_performance(self, operation: str, duration_ms: float, **kw: Any) -> None:
        self.info("performance", operation=operation, duration_ms=f"{duration_ms:.2f}", **kw)

    def log_error_with_context(self, message: str, error: Exception | None = None, **kw: Any) -> None:
        if error is not None:
            kw["error_type"] = error.__class__.__name__
            kw["error"] = str(error)
        self.error(message, **kw)


class TimerContext:
    def __init__(self, logger: StructuredLogger, operation: str):
        self.logger = logger
        self.operation = operation
        self._start = 0.0

    def __enter__(self) -> TimerContext:
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type: type[BaseException] | None, exc: BaseException | None, _tb: TracebackType | None) -> bool:
        elapsed_ms = (time.perf_counter() - self._start) * 1000
        if exc is None:
            self.logger.log_performance(self.operation, elapsed_ms)
        elif isinstance(exc, Exception):
            self.logger.log_error_with_context(f"{self.operation}_failed", error=exc, duration_ms=f"{elapsed_ms:.2f}")
        return False

    async def __aenter__(self) -> TimerContext:
        return self.__enter__()

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return self.__exit__(exc_type, exc, tb)


class PipelineTracer:
    """In-memory pipeline step collector. Single DB write at end."""

    def __init__(self, logger: StructuredLogger):
        self._logger = logger
        self._steps: list[dict[str, Any]] = []
        self._start = time.perf_counter()

    def step(self, name: str, status: str = "ok", duration_ms: float | None = None, **data: Any) -> None:
        entry: dict[str, Any] = {"name": name, "status": status, "ts": datetime.now().isoformat()}
        if duration_ms is not None:
            entry["duration_ms"] = round(duration_ms, 1)
        if data:
            entry["data"] = {
                k: str(v) if not isinstance(v, (int, float, bool, type(None))) else v
                for k, v in data.items()
            }
        self._steps.append(entry)
        self._logger.info(f"pipeline_step:{name}", status=status, **(data or {}))

    @asynccontextmanager
    async def timed_step(self, name: str, **data: Any):
        start = time.perf_counter()
        try:
            yield
            elapsed = (time.perf_counter() - start) * 1000
            self.step(name, status="ok", duration_ms=elapsed, **data)
        except Exception as exc:
            elapsed = (time.perf_counter() - start) * 1000
            self.step(name, status="error", duration_ms=elapsed, error=str(exc), **data)
            raise

    def to_dict(self) -> dict[str, Any]:
        total = (time.perf_counter() - self._start) * 1000
        return {
            "total_duration_ms": round(total, 1),
            "step_count": len(self._steps),
            "steps": self._steps,
        }


def get_logger(name: str, request_id: str | None = None) -> StructuredLogger:
    return StructuredLogger(name, request_id)


def log_execution_time(logger: StructuredLogger, operation_name: str) -> Callable:
    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: P.args, **kwargs: P.kwargs):
                async with TimerContext(logger, operation_name):
                    return await func(*args, **kwargs)
            return async_wrapper  # type: ignore[return-value]

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs):
            with TimerContext(logger, operation_name):
                return func(*args, **kwargs)
        return sync_wrapper  # type: ignore[return-value]

    return decorator
