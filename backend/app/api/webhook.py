from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_request_id
from app.core.logging import get_logger
from app.models import Project, WebhookLog
from app.queue.types import TaskPayload, TaskPriority

router = APIRouter()


async def _ensure_project(payload: dict[str, Any], db: AsyncSession) -> Project:
    project_data = payload.get("project")
    if not isinstance(project_data, dict):
        project_data = {}

    project_id_raw = project_data.get("id", payload.get("project_id"))
    try:
        project_id = int(project_id_raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Missing project id in webhook payload.")

    project = (
        await db.execute(select(Project).where(Project.project_id == project_id).limit(1))
    ).scalars().first()

    project_name = str(project_data.get("name") or project_data.get("path_with_namespace") or f"project-{project_id}")
    project_path = str(project_data.get("path_with_namespace") or project_data.get("path") or project_name)
    project_url = str(project_data.get("web_url") or project_data.get("git_http_url") or "")
    namespace = str(project_data.get("namespace") or "default")

    if project is None:
        project = Project(
            project_id=project_id,
            project_name=project_name[:255],
            project_path=project_path[:500],
            project_url=project_url[:500],
            namespace=namespace[:255],
            review_enabled=True,
            auto_review_on_mr=True,
            gitlab_comment_notifications_enabled=True,
            enabled_webhook_events=[],
            exclude_file_types=[],
            ignore_file_patterns=[],
            gitlab_data=project_data,
        )
        db.add(project)
        await db.flush()
        return project

    project.project_name = project_name[:255]
    project.project_path = project_path[:500]
    if project_url:
        project.project_url = project_url[:500]
    project.namespace = namespace[:255]
    project.gitlab_data = project_data
    return project


@router.post("/gitlab/")
async def handle_gitlab_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    request_id: str | None = Depends(get_request_id),
) -> dict[str, Any]:
    logger = get_logger(__name__, request_id)
    queue_manager = getattr(request.app.state, "queue_manager", None)
    if queue_manager is None:
        raise HTTPException(status_code=503, detail="Queue manager is not available.")

    try:
        payload = await request.json()
    except Exception as exc:
        logger.log_error_with_context("webhook_invalid_json", error=exc)
        raise HTTPException(status_code=400, detail="Invalid JSON body.") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Webhook payload must be a JSON object.")

    project = await _ensure_project(payload, db)

    attributes = payload.get("object_attributes")
    if not isinstance(attributes, dict):
        attributes = {}
    user = payload.get("user")
    if not isinstance(user, dict):
        user = {}

    event_type = request.headers.get("X-Gitlab-Event", "Unknown Event")
    mr_iid_raw = attributes.get("iid")
    try:
        merge_request_iid = int(mr_iid_raw) if mr_iid_raw is not None else None
    except (TypeError, ValueError):
        merge_request_iid = None

    source_branch = str(attributes.get("source_branch") or "")
    target_branch = str(attributes.get("target_branch") or "")

    webhook_log = WebhookLog(
        event_type=event_type[:100],
        project_id=project.project_id,
        project_name=project.project_name[:255],
        merge_request_iid=merge_request_iid,
        user_name=str(user.get("name") or "unknown")[:255],
        user_email=str(user.get("email") or "")[:255],
        source_branch=source_branch[:255],
        target_branch=target_branch[:255],
        payload=payload,
        request_headers=dict(request.headers),
        request_body_raw=json.dumps(payload, ensure_ascii=False),
        remote_addr=(request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        request_id=request_id,
        processed=False,
        log_level="INFO",
    )
    db.add(webhook_log)
    await db.flush()

    task_payload = TaskPayload(
        task_type="review_mr",
        data={
            "payload": payload,
            "project_id": project.project_id,
            "webhook_log_id": webhook_log.id,
            "event_type": event_type,
            "request_id": request_id,
        },
        priority=TaskPriority.normal,
        max_retries=3,
    )

    task_id = await queue_manager.enqueue(task_payload)
    await db.commit()
    logger.info(
        "webhook_enqueued",
        task_id=task_id,
        webhook_log_id=webhook_log.id,
        project_id=project.project_id,
        event_type=event_type,
    )
    return {
        "code": 202,
        "message": "Webhook accepted",
        "task_id": task_id,
        "log_id": webhook_log.id,
    }


@router.get("/webhook-url/")
async def get_webhook_url(request: Request) -> dict[str, Any]:
    base = str(request.base_url).rstrip("/")
    return {"webhook_url": f"{base}/api/webhook/gitlab/"}
