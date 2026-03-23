from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy import select, func, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_db, get_request_id
from app.core.logging import get_logger
from app.models import (
    GitLabConfig,
    LLMProvider,
    NotificationChannel,
    Project,
    ProjectNotificationSetting,
    ProjectWebhookEventPrompt,
    WebhookEventRule,
    WebhookLog,
    MergeRequestReview,
)
from app.schemas.project import (
    GitLabProjectSearchItem,
    ProjectImport,
    ProjectImportResultItem,
    ProjectListResponse,
    ProjectNotificationSettingResponse,
    ProjectNotificationUpdate,
    ProjectResponse,
    ProjectUpdate,
    ProjectWebhookEventPromptResponse,
    ProjectWebhookEventPromptUpdate,
)
from app.schemas.review import MergeRequestReviewResponse
from app.schemas.event_rule import WebhookEventRuleResponse
from app.schemas.webhook import WebhookLogResponse
from app.services.gitlab import GitLabService

router = APIRouter()


def _webhook_url(request: Request) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/webhook/gitlab/"


def _to_project_response(project: Project, request: Request) -> ProjectResponse:
    payload = ProjectResponse.model_validate(project, from_attributes=True)
    return payload.model_copy(update={"webhook_url": _webhook_url(request)})


def _to_project_list_response(project: Project, request: Request) -> ProjectListResponse:
    payload = ProjectListResponse.model_validate(project, from_attributes=True)
    gitlab_data = project.gitlab_data if isinstance(project.gitlab_data, dict) else {}
    description = str(gitlab_data.get("description") or "")
    last_activity = _resolve_last_activity_text(
        gitlab_data.get("last_activity_at"),
        project.last_webhook_at,
    )
    return payload.model_copy(
        update={
            "description": description,
            "last_activity": last_activity,
            "webhook_url": _webhook_url(request),
        }
    )


def _parse_datetime_like(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _resolve_last_activity_text(*values: Any) -> str | None:
    candidates = [item for item in (_parse_datetime_like(v) for v in values) if item is not None]
    if not candidates:
        return None
    latest = max(candidates)
    return latest.strftime("%Y-%m-%d %H:%M")


async def _build_project_list_stats(
    db: AsyncSession,
    project_ids: list[int],
) -> dict[int, dict[str, Any]]:
    if not project_ids:
        return {}

    stats_map: dict[int, dict[str, Any]] = {
        pid: {
            "commits_count": 0,
            "mr_count": 0,
            "members_count": 0,
            "weekly_reviews": 0,
            "recent_events_count": 0,
            "last_event_at": None,
        }
        for pid in project_ids
    }

    push_rows = (
        await db.execute(
            select(WebhookLog.project_id, func.count())
            .where(
                WebhookLog.project_id.in_(project_ids),
                WebhookLog.event_type == "Push Hook",
            )
            .group_by(WebhookLog.project_id)
        )
    ).all()
    for project_id, push_count in push_rows:
        stats_map[int(project_id)]["commits_count"] = int(push_count or 0)

    mr_rows = (
        await db.execute(
            select(WebhookLog.project_id, func.count(distinct(WebhookLog.merge_request_iid)))
            .where(
                WebhookLog.project_id.in_(project_ids),
                WebhookLog.event_type == "Merge Request Hook",
                WebhookLog.merge_request_iid.isnot(None),
            )
            .group_by(WebhookLog.project_id)
        )
    ).all()
    for project_id, mr_count in mr_rows:
        stats_map[int(project_id)]["mr_count"] = int(mr_count or 0)

    contributor_rows = (
        await db.execute(
            select(WebhookLog.project_id, func.count(distinct(WebhookLog.user_name)))
            .where(
                WebhookLog.project_id.in_(project_ids),
                WebhookLog.user_name.isnot(None),
                WebhookLog.user_name != "",
                WebhookLog.user_name != "unknown",
            )
            .group_by(WebhookLog.project_id)
        )
    ).all()
    for project_id, members_count in contributor_rows:
        stats_map[int(project_id)]["members_count"] = int(members_count or 0)

    recent_rows = (
        await db.execute(
            select(
                WebhookLog.project_id,
                func.count(WebhookLog.id),
                func.max(WebhookLog.created_at),
            )
            .where(WebhookLog.project_id.in_(project_ids))
            .group_by(WebhookLog.project_id)
        )
    ).all()
    for project_id, event_count, last_event_at in recent_rows:
        stats_map[int(project_id)]["recent_events_count"] = int(event_count or 0)
        stats_map[int(project_id)]["last_event_at"] = last_event_at

    week_ago = datetime.now() - timedelta(days=7)
    review_rows = (
        await db.execute(
            select(MergeRequestReview.project_id, func.count(MergeRequestReview.id))
            .where(
                MergeRequestReview.project_id.in_(project_ids),
                MergeRequestReview.created_at >= week_ago,
            )
            .group_by(MergeRequestReview.project_id)
        )
    ).all()
    for project_id, weekly_reviews in review_rows:
        stats_map[int(project_id)]["weekly_reviews"] = int(weekly_reviews or 0)

    return stats_map


async def _get_project_or_404(project_id: int, db: AsyncSession) -> Project:
    project = (
        await db.execute(
            select(Project).where(Project.project_id == project_id).limit(1)
        )
    ).scalars().first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    return project


@router.get("/projects/stats/")
async def get_projects_stats(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    projects = (await db.execute(select(Project))).scalars().all()
    total = len(projects)
    enabled = len([project for project in projects if project.review_enabled])

    week_ago = datetime.now() - timedelta(days=7)

    weekly_reviews = (
        await db.execute(
            select(func.count())
            .select_from(MergeRequestReview)
            .where(MergeRequestReview.created_at >= week_ago)
        )
    ).scalar() or 0

    recent_events = (
        await db.execute(
            select(func.count())
            .select_from(WebhookLog)
            .where(WebhookLog.created_at >= week_ago)
        )
    ).scalar() or 0

    return {
        "total_projects": total,
        "enabled_projects": enabled,
        "weekly_reviews": weekly_reviews,
        "recent_events": recent_events,
    }


@router.get("/projects/gitlab-search/")
async def search_gitlab_projects(
    search: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    request_id: str | None = Depends(get_request_id),
) -> dict[str, Any]:
    logger = get_logger(__name__, request_id)
    svc = GitLabService(db, request_id)
    items, total = await svc.list_projects(search=search, page=page, per_page=per_page)

    if items:
        gitlab_ids = [item["id"] for item in items]
        existing = (
            await db.execute(select(Project.project_id).where(Project.project_id.in_(gitlab_ids)))
        ).scalars().all()
        existing_set = set(existing)
    else:
        existing_set = set()

    results = [
        GitLabProjectSearchItem(
            id=item["id"],
            name=item["name"],
            path_with_namespace=item["path_with_namespace"],
            web_url=item["web_url"],
            namespace=item["namespace"],
            description=item["description"],
            last_activity_at=item.get("last_activity_at"),
            imported=item["id"] in existing_set,
        )
        for item in items
    ]
    logger.info("gitlab_projects_searched", search=search, count=len(results), total=total)
    return {"count": total, "page": page, "results": results}


@router.post("/projects/import/")
async def import_projects(
    payload: ProjectImport,
    db: AsyncSession = Depends(get_db),
    request_id: str | None = Depends(get_request_id),
) -> dict[str, Any]:
    logger = get_logger(__name__, request_id)
    svc = GitLabService(db, request_id)

    webhook_url: str | None = None
    if payload.auto_register_webhook:
        gitlab_config = (
            await db.execute(
                select(GitLabConfig)
                .where(GitLabConfig.is_active.is_(True))
                .order_by(GitLabConfig.updated_at.desc())
                .limit(1)
            )
        ).scalars().first()
        site_url = gitlab_config.site_url if gitlab_config else ""
        if not site_url:
            raise HTTPException(
                status_code=400,
                detail="site_url is not configured. Please set it in Config → GitLab tab first.",
            )
        webhook_url = f"{site_url.rstrip('/')}/api/webhook/gitlab/"

    imported: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for pid in payload.project_ids:
        try:
            info = await svc.get_project_info(pid)
        except Exception as exc:
            failed.append(ProjectImportResultItem(
                project_id=pid, success=False, error=str(exc),
            ).model_dump())
            continue

        project_name = str(info.get("name") or info.get("path_with_namespace") or f"project-{pid}")
        project_path = str(info.get("path_with_namespace") or info.get("path") or project_name)
        project_url = str(info.get("web_url") or "")
        ns = info.get("namespace") or {}
        namespace = ns.get("full_path", "") if isinstance(ns, dict) else str(ns)

        existing = (
            await db.execute(select(Project).where(Project.project_id == pid).limit(1))
        ).scalars().first()

        if existing is None:
            project = Project(
                project_id=pid,
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
                gitlab_data=info,
            )
            db.add(project)
            await db.flush()
        else:
            existing.project_name = project_name[:255]
            existing.project_path = project_path[:500]
            if project_url:
                existing.project_url = project_url[:500]
            existing.namespace = namespace[:255]
            existing.gitlab_data = info
            existing.review_enabled = True

        result_item = ProjectImportResultItem(
            project_id=pid, name=project_name, success=True,
        )

        if webhook_url:
            hook_result = await svc.create_project_hook(pid, webhook_url)
            result_item.webhook_registered = hook_result.get("success", False)
            if not hook_result.get("success"):
                result_item.error = hook_result.get("error")

        imported.append(result_item.model_dump())

    await db.commit()
    logger.info(
        "projects_imported",
        imported=len(imported),
        failed=len(failed),
    )
    return {"imported": imported, "failed": failed}


@router.get("/projects/")
async def list_projects(
    request: Request,
    page: int = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    settings = get_settings()
    page_size = settings.PAGE_SIZE
    offset = (page - 1) * page_size

    count = len((await db.execute(select(Project.id))).all())
    projects = (
        await db.execute(
            select(Project)
            .order_by(Project.created_at.desc(), Project.id.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).scalars().all()
    project_ids = [int(item.project_id) for item in projects]
    stats_map = await _build_project_list_stats(db, project_ids)
    results: list[ProjectListResponse] = []
    for project in projects:
        project_stats = stats_map.get(int(project.project_id), {})
        payload = _to_project_list_response(project, request)
        last_activity = _resolve_last_activity_text(
            project_stats.get("last_event_at"),
            payload.last_activity,
            project.last_webhook_at,
        )
        results.append(
            payload.model_copy(
                update={
                    "commits_count": int(project_stats.get("commits_count") or 0),
                    "mr_count": int(project_stats.get("mr_count") or 0),
                    "members_count": int(project_stats.get("members_count") or 0),
                    "weekly_reviews": int(project_stats.get("weekly_reviews") or 0),
                    "recent_events_count": int(project_stats.get("recent_events_count") or 0),
                    "last_activity": last_activity,
                }
            )
        )
    return {
        "count": count,
        "results": results,
    }


@router.get("/projects/{project_id}/", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    project = await _get_project_or_404(project_id, db)
    return _to_project_response(project, request)


@router.post("/projects/{project_id}/enable/")
async def enable_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    request_id: str | None = Depends(get_request_id),
) -> dict[str, Any]:
    project = await _get_project_or_404(project_id, db)
    project.review_enabled = True
    await db.commit()
    logger = get_logger(__name__, request_id)
    logger.info("project_enabled", project_id=project_id)
    return {"code": 200, "message": "Project enabled", "project_id": project_id}


@router.post("/projects/{project_id}/disable/")
async def disable_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    request_id: str | None = Depends(get_request_id),
) -> dict[str, Any]:
    project = await _get_project_or_404(project_id, db)
    project.review_enabled = False
    await db.commit()
    logger = get_logger(__name__, request_id)
    logger.info("project_disabled", project_id=project_id)
    return {"code": 200, "message": "Project disabled", "project_id": project_id}


@router.post("/projects/{project_id}/update/", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    request: Request,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    project = await _get_project_or_404(project_id, db)
    update_data = payload.model_dump(exclude_unset=True)

    if "default_llm_provider_id" in update_data:
        provider_id = update_data["default_llm_provider_id"]
        if provider_id is None or provider_id == 0:
            update_data["default_llm_provider_id"] = None
        else:
            provider = await db.get(LLMProvider, provider_id)
            if provider is None or not provider.is_active:
                raise HTTPException(status_code=404, detail="LLM provider not found or inactive.")

    for field, value in update_data.items():
        setattr(project, field, value)
    await db.commit()
    await db.refresh(project)
    return _to_project_response(project, request)


@router.get("/projects/{project_id}/webhook-logs/")
async def get_project_webhook_logs(
    project_id: int,
    page: int = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    settings = get_settings()
    page_size = settings.PAGE_SIZE
    offset = (page - 1) * page_size

    _ = await _get_project_or_404(project_id, db)
    logs = (
        await db.execute(
            select(WebhookLog)
            .where(WebhookLog.project_id == project_id)
            .order_by(WebhookLog.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).scalars().all()
    count = len((await db.execute(select(WebhookLog.id).where(WebhookLog.project_id == project_id))).all())
    return {
        "count": count,
        "results": [WebhookLogResponse.model_validate(log, from_attributes=True) for log in logs],
    }


@router.get("/projects/{project_id}/stats/")
async def get_project_stats(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    _ = await _get_project_or_404(project_id, db)
    now = datetime.now()
    week_ago = now - timedelta(days=7)

    push_count = (
        await db.execute(
            select(func.count())
            .select_from(WebhookLog)
            .where(WebhookLog.project_id == project_id, WebhookLog.event_type == "Push Hook")
        )
    ).scalar() or 0

    mr_count = (
        await db.execute(
            select(func.count(distinct(WebhookLog.merge_request_iid)))
            .select_from(WebhookLog)
            .where(
                WebhookLog.project_id == project_id,
                WebhookLog.event_type == "Merge Request Hook",
                WebhookLog.merge_request_iid.isnot(None),
            )
        )
    ).scalar() or 0

    members_count = (
        await db.execute(
            select(func.count(distinct(WebhookLog.user_name)))
            .select_from(WebhookLog)
            .where(WebhookLog.project_id == project_id, WebhookLog.user_name != "unknown")
        )
    ).scalar() or 0

    review_base = select(MergeRequestReview).where(MergeRequestReview.project_id == project_id)
    total_reviews = (await db.execute(select(func.count()).select_from(review_base.subquery()))).scalar() or 0
    completed_reviews = (
        await db.execute(
            select(func.count())
            .select_from(MergeRequestReview)
            .where(MergeRequestReview.project_id == project_id, MergeRequestReview.status == "completed")
        )
    ).scalar() or 0
    failed_reviews = (
        await db.execute(
            select(func.count())
            .select_from(MergeRequestReview)
            .where(MergeRequestReview.project_id == project_id, MergeRequestReview.status == "failed")
        )
    ).scalar() or 0
    weekly_reviews = (
        await db.execute(
            select(func.count())
            .select_from(MergeRequestReview)
            .where(MergeRequestReview.project_id == project_id, MergeRequestReview.created_at >= week_ago)
        )
    ).scalar() or 0

    completion_rate = (completed_reviews / total_reviews * 100) if total_reviews > 0 else 0.0

    return {
        "commits_count": push_count,
        "mr_count": mr_count,
        "members_count": members_count,
        "reviews": {
            "total": total_reviews,
            "completed": completed_reviews,
            "failed": failed_reviews,
            "weekly": weekly_reviews,
            "completion_rate": round(completion_rate, 1),
        },
    }


@router.get("/projects/{project_id}/review-history/")
async def get_project_review_history(
    project_id: int,
    page: int = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    settings = get_settings()
    page_size = settings.PAGE_SIZE
    offset = (page - 1) * page_size

    _ = await _get_project_or_404(project_id, db)
    reviews = (
        await db.execute(
            select(MergeRequestReview)
            .where(MergeRequestReview.project_id == project_id)
            .order_by(MergeRequestReview.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).scalars().all()
    count = len((await db.execute(select(MergeRequestReview.id).where(MergeRequestReview.project_id == project_id))).all())
    return {
        "count": count,
        "results": [MergeRequestReviewResponse.model_validate(item, from_attributes=True) for item in reviews],
    }


@router.get("/projects/{project_id}/notifications/")
async def get_project_notifications(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    project = await _get_project_or_404(project_id, db)
    rows = (
        await db.execute(
            select(ProjectNotificationSetting, NotificationChannel)
            .join(
                NotificationChannel,
                NotificationChannel.id == ProjectNotificationSetting.channel_id,
            )
            .where(
                ProjectNotificationSetting.project_id == project.id,
                NotificationChannel.notification_type != "gitlab",
            )
            .order_by(NotificationChannel.updated_at.desc())
        )
    ).all()

    channels: list[ProjectNotificationSettingResponse] = []
    for setting, channel in rows:
        channels.append(
            ProjectNotificationSettingResponse(
                channel_id=channel.id,
                channel_name=channel.name,
                notification_type=channel.notification_type,
                enabled=setting.enabled,
            )
        )
    return {
        "project_id": project.project_id,
        "gitlab_comment_enabled": project.gitlab_comment_notifications_enabled,
        "channels": channels,
    }


@router.post("/projects/{project_id}/notifications/update/")
async def update_project_notifications(
    project_id: int,
    payload: ProjectNotificationUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    project = await _get_project_or_404(project_id, db)
    if payload.gitlab_comment_enabled is not None:
        project.gitlab_comment_notifications_enabled = payload.gitlab_comment_enabled

    desired_ids: set[int] = set()
    for channel_id in set(payload.channel_ids):
        channel = await db.get(NotificationChannel, channel_id)
        if channel is None or channel.notification_type == "gitlab":
            continue
        desired_ids.add(channel_id)
    existing_rows = (
        await db.execute(
            select(ProjectNotificationSetting).where(ProjectNotificationSetting.project_id == project.id)
        )
    ).scalars().all()

    existing_by_channel: dict[int, ProjectNotificationSetting] = {
        item.channel_id: item for item in existing_rows
    }
    for channel_id, row in existing_by_channel.items():
        row.enabled = channel_id in desired_ids

    for channel_id in desired_ids:
        if channel_id in existing_by_channel:
            continue
        db.add(
            ProjectNotificationSetting(
                project_id=project.id,
                channel_id=channel_id,
                enabled=True,
            )
        )

    await db.commit()
    return {"code": 200, "message": "Project notification settings updated"}


@router.get("/projects/{project_id}/webhook-events/")
async def get_project_webhook_events(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    project = await _get_project_or_404(project_id, db)
    rules = (
        await db.execute(
            select(WebhookEventRule)
            .where(WebhookEventRule.is_active.is_(True))
            .order_by(WebhookEventRule.updated_at.desc())
        )
    ).scalars().all()
    return {
        "project_id": project.project_id,
        "enabled_webhook_events": list(project.enabled_webhook_events or []),
        "available_rules": [WebhookEventRuleResponse.model_validate(rule, from_attributes=True) for rule in rules],
    }


@router.post("/projects/{project_id}/webhook-events/")
async def create_project_webhook_events(
    project_id: int,
    body: dict[str, Any] = Body(default_factory=dict),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    project = await _get_project_or_404(project_id, db)
    value = body.get("enabled_webhook_events")
    if not isinstance(value, list):
        raise HTTPException(status_code=400, detail="Field 'enabled_webhook_events' must be a list.")
    enabled_ids = [int(item) for item in value if isinstance(item, int) or (isinstance(item, str) and item.isdigit())]
    project.enabled_webhook_events = enabled_ids
    await db.commit()
    return {"code": 200, "message": "Project webhook events saved", "enabled_webhook_events": enabled_ids}


@router.post("/projects/{project_id}/webhook-events/update/")
async def update_project_webhook_events(
    project_id: int,
    body: dict[str, Any] = Body(default_factory=dict),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    project = await _get_project_or_404(project_id, db)
    source = body.get("enabled_webhook_events")
    if source is None:
        source = body.get("event_rule_ids")
    if not isinstance(source, list):
        raise HTTPException(
            status_code=400,
            detail="Field 'enabled_webhook_events' or 'event_rule_ids' must be a list.",
        )
    enabled_ids = [int(item) for item in source if isinstance(item, int) or (isinstance(item, str) and item.isdigit())]
    project.enabled_webhook_events = enabled_ids
    await db.commit()
    return {"code": 200, "message": "Project webhook events updated", "enabled_webhook_events": enabled_ids}


@router.get("/projects/{project_id}/webhook-event-prompts/")
async def get_project_webhook_event_prompts(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    project = await _get_project_or_404(project_id, db)
    rows = (
        await db.execute(
            select(ProjectWebhookEventPrompt, WebhookEventRule)
            .join(
                WebhookEventRule,
                WebhookEventRule.id == ProjectWebhookEventPrompt.event_rule_id,
            )
            .where(ProjectWebhookEventPrompt.project_id == project.id)
            .order_by(ProjectWebhookEventPrompt.updated_at.desc())
        )
    ).all()

    results: list[ProjectWebhookEventPromptResponse] = []
    for prompt, rule in rows:
        results.append(
            ProjectWebhookEventPromptResponse(
                id=prompt.id,
                project=prompt.project_id,
                event_rule=prompt.event_rule_id,
                event_rule_name=rule.name,
                event_rule_type=rule.event_type,
                event_rule_description=rule.description,
                custom_prompt=prompt.custom_prompt,
                use_custom=prompt.use_custom,
                created_at=prompt.created_at,
                updated_at=prompt.updated_at,
            )
        )
    return {"count": len(results), "results": results}


@router.post("/projects/{project_id}/webhook-event-prompts/update/")
async def update_project_webhook_event_prompt(
    project_id: int,
    payload: ProjectWebhookEventPromptUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    project = await _get_project_or_404(project_id, db)
    rule = await db.get(WebhookEventRule, payload.event_rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Webhook event rule not found.")

    prompt = (
        await db.execute(
            select(ProjectWebhookEventPrompt)
            .where(
                ProjectWebhookEventPrompt.project_id == project.id,
                ProjectWebhookEventPrompt.event_rule_id == payload.event_rule_id,
            )
            .limit(1)
        )
    ).scalars().first()

    if prompt is None:
        prompt = ProjectWebhookEventPrompt(
            project_id=project.id,
            event_rule_id=payload.event_rule_id,
            custom_prompt=payload.custom_prompt,
            use_custom=payload.use_custom,
        )
        db.add(prompt)
    else:
        prompt.custom_prompt = payload.custom_prompt
        prompt.use_custom = payload.use_custom

    await db.commit()
    await db.refresh(prompt)
    return {
        "code": 200,
        "message": "Project webhook event prompt updated",
        "result": ProjectWebhookEventPromptResponse(
            id=prompt.id,
            project=prompt.project_id,
            event_rule=prompt.event_rule_id,
            event_rule_name=rule.name,
            event_rule_type=rule.event_type,
            event_rule_description=rule.description,
            custom_prompt=prompt.custom_prompt,
            use_custom=prompt.use_custom,
            created_at=prompt.created_at,
            updated_at=prompt.updated_at,
        ),
    }
