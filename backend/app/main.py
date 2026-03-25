from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    config,
    event_rules,
    llm,
    mr_feedback,
    notifications,
    projects,
    reports,
    reviews,
    system,
    webhook,
)
from app.config import get_settings
from app.core.auth import get_current_user
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestIDMiddleware, RequestTimingMiddleware
from app.database import init_db
from app.queue.manager import QueueManager
from app.services.reporting.weekly_snapshot_scheduler import DeveloperWeeklySnapshotScheduler

import app.models  # noqa: F401 — register all model metadata before init_db

queue_manager = QueueManager()
weekly_snapshot_scheduler = DeveloperWeeklySnapshotScheduler(queue_manager)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    settings.ensure_directories()
    configure_logging(
        settings.LOG_LEVEL,
        settings.LOG_DIR,
        settings.LOG_FILE_MAX_BYTES,
        settings.LOG_FILE_BACKUP_COUNT,
    )

    logger = get_logger(__name__)
    logger.info(
        "application_starting",
        debug=settings.DEBUG,
        queue_backend=settings.TASK_QUEUE_BACKEND.value,
    )

    await init_db()
    await queue_manager.start_worker()
    await weekly_snapshot_scheduler.start()
    _app.state.queue_manager = queue_manager
    try:
        yield
    finally:
        await weekly_snapshot_scheduler.stop()
        await queue_manager.stop_worker()
        logger.info("application_stopped")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Code Review GPT API v2",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Middleware (order matters: outermost first)
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    cors_kwargs: dict = {
        "allow_credentials": True,
        "allow_methods": ["DELETE", "GET", "OPTIONS", "PATCH", "POST", "PUT"],
        "allow_headers": [
            "accept", "accept-encoding", "authorization", "content-type",
            "dnt", "origin", "user-agent", "x-csrftoken",
            "x-requested-with", "x-gitlab-token",
        ],
        "max_age": 86400,
    }
    if settings.DEBUG:
        cors_kwargs["allow_origins"] = []
        cors_kwargs["allow_origin_regex"] = ".*"
    else:
        cors_kwargs["allow_origins"] = settings.CORS_ORIGINS

    app.add_middleware(CORSMiddleware, **cors_kwargs)

    register_exception_handlers(app)

    @app.get("/health/")
    async def health_check():
        return {"status": "ok", "message": "Code Review GPT API v2"}

    protected_dependencies = [Depends(get_current_user)]

    app.include_router(auth.router, prefix="/api", tags=["auth"])
    app.include_router(webhook.router, prefix="/api/webhook", tags=["webhook"])
    app.include_router(
        projects.router,
        prefix="/api/webhook",
        tags=["projects"],
        dependencies=protected_dependencies,
    )
    app.include_router(
        reviews.router,
        prefix="/api/webhook",
        tags=["reviews"],
        dependencies=protected_dependencies,
    )
    app.include_router(
        mr_feedback.router,
        prefix="/api/webhook",
        tags=["mr-feedback"],
        dependencies=protected_dependencies,
    )
    app.include_router(
        reports.router,
        prefix="/api/webhook",
        tags=["reports"],
    )
    app.include_router(llm.router, prefix="/api", tags=["llm"], dependencies=protected_dependencies)
    app.include_router(config.router, prefix="/api", tags=["config"], dependencies=protected_dependencies)
    app.include_router(
        notifications.router,
        prefix="/api",
        tags=["notifications"],
        dependencies=protected_dependencies,
    )
    app.include_router(
        event_rules.router,
        prefix="/api",
        tags=["event-rules"],
        dependencies=protected_dependencies,
    )
    app.include_router(system.router, prefix="/api", tags=["system"], dependencies=protected_dependencies)

    return app


app = create_app()
