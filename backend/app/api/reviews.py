from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.models import MergeRequestReview, ReviewFinding, ReviewFindingAction, WebhookLog
from app.schemas.review import (
    MergeRequestReviewResponse,
    ReviewFindingActionCreate,
    ReviewFindingBatchActionCreate,
    ReviewFindingBatchActionResponse,
    ReviewFindingActionResponse,
    ReviewFindingResponse,
    ReviewFindingWorkbenchItem,
    ReviewFindingWorkbenchListResponse,
    ReviewFindingWorkbenchReviewMeta,
    ReviewFindingStatsResponse,
    ReviewStatsBucket,
)
from app.schemas.webhook import WebhookLogResponse
from app.services.review_structured import materialize_review_findings_from_legacy

router = APIRouter()

ALLOWED_ACTION_STATUSES = ("unprocessed", "fixed", "todo", "ignored", "reopened")
LEGACY_MATERIALIZATION_BATCH_SIZE = 200


def _to_bucket_rows(rows: list[tuple[Any, Any]]) -> list[ReviewStatsBucket]:
    result: list[ReviewStatsBucket] = []
    for name, value in rows:
        label = str(name or "unknown")
        count = int(value or 0)
        result.append(ReviewStatsBucket(name=label, value=count))
    return result


async def _materialize_legacy_findings_for_workbench(
    db: AsyncSession,
    *,
    project_id: int | None,
    normalized_review_statuses: list[str],
    author: str | None,
    limit: int = LEGACY_MATERIALIZATION_BATCH_SIZE,
) -> None:
    stmt = (
        select(MergeRequestReview)
        .outerjoin(ReviewFinding, ReviewFinding.review_id == MergeRequestReview.id)
        .where(ReviewFinding.id.is_(None))
        .order_by(MergeRequestReview.created_at.desc(), MergeRequestReview.id.desc())
        .limit(limit)
    )
    if project_id is not None:
        stmt = stmt.where(MergeRequestReview.project_id == project_id)
    if normalized_review_statuses:
        stmt = stmt.where(MergeRequestReview.status.in_(normalized_review_statuses))
    if author:
        pattern = f"%{author.strip()}%"
        stmt = stmt.where(
            or_(
                MergeRequestReview.author_name.ilike(pattern),
                MergeRequestReview.author_email.ilike(pattern),
            )
        )

    candidates = (await db.execute(stmt)).scalars().all()
    for review in candidates:
        if not isinstance(review.review_issues, list) or not review.review_issues:
            continue
        await materialize_review_findings_from_legacy(db, review=review)


@router.get("/dashboard/stats/")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    today_reviews = (
        await db.execute(
            select(func.count())
            .select_from(MergeRequestReview)
            .where(MergeRequestReview.created_at >= today_start)
        )
    ).scalar() or 0

    yesterday_reviews = (
        await db.execute(
            select(func.count())
            .select_from(MergeRequestReview)
            .where(
                MergeRequestReview.created_at >= yesterday_start,
                MergeRequestReview.created_at < today_start,
            )
        )
    ).scalar() or 0

    today_growth = (
        round((today_reviews - yesterday_reviews) / yesterday_reviews * 100)
        if yesterday_reviews > 0
        else (100 if today_reviews > 0 else 0)
    )

    week_reviews = (
        await db.execute(
            select(func.count())
            .select_from(MergeRequestReview)
            .where(MergeRequestReview.created_at >= week_ago)
        )
    ).scalar() or 0

    row = (
        await db.execute(
            select(
                func.count().label("total"),
                func.count(case((MergeRequestReview.status == "completed", 1))).label("completed"),
            )
            .select_from(MergeRequestReview)
        )
    ).one()
    total_reviews = row.total or 0
    completed_reviews = row.completed or 0
    success_rate = round(completed_reviews / total_reviews * 100, 1) if total_reviews > 0 else 0.0

    llm_calls = (
        await db.execute(
            select(func.count())
            .select_from(MergeRequestReview)
            .where(MergeRequestReview.created_at >= today_start, MergeRequestReview.llm_provider.isnot(None))
        )
    ).scalar() or 0

    return {
        "today_reviews": today_reviews,
        "today_growth": today_growth,
        "week_reviews": week_reviews,
        "llm_calls": llm_calls,
        "success_rate": success_rate,
    }


@router.get("/dashboard/charts/")
async def get_dashboard_charts(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    now = datetime.utcnow()
    start = now - timedelta(days=days)

    # --- review trend (per-day counts) ---
    date_expr = func.date(MergeRequestReview.created_at)
    trend_rows = (
        await db.execute(
            select(
                date_expr.label("day"),
                func.count().label("reviews"),
                func.count(case((MergeRequestReview.llm_provider.isnot(None), 1))).label("llm_calls"),
            )
            .where(MergeRequestReview.created_at >= start)
            .group_by(date_expr)
            .order_by(date_expr)
        )
    ).all()
    trend_map = {str(r.day): {"reviews": r.reviews, "llm_calls": r.llm_calls} for r in trend_rows}
    dates = []
    reviews_data = []
    llm_data = []
    for i in range(days):
        d = (start + timedelta(days=i + 1)).strftime("%Y-%m-%d")
        dates.append(d[5:])  # "MM-DD"
        entry = trend_map.get(d, {"reviews": 0, "llm_calls": 0})
        reviews_data.append(entry["reviews"])
        llm_data.append(entry["llm_calls"])

    # --- LLM model distribution ---
    model_rows = (
        await db.execute(
            select(
                MergeRequestReview.llm_model,
                func.count().label("cnt"),
            )
            .where(MergeRequestReview.llm_model.isnot(None), MergeRequestReview.llm_model != "")
            .group_by(MergeRequestReview.llm_model)
            .order_by(func.count().desc())
        )
    ).all()
    llm_distribution = [{"name": r.llm_model, "value": r.cnt} for r in model_rows]

    # --- review status distribution ---
    status_rows = (
        await db.execute(
            select(
                MergeRequestReview.status,
                func.count().label("cnt"),
            )
            .group_by(MergeRequestReview.status)
        )
    ).all()
    status_label_map = {
        "completed": "已完成", "failed": "失败",
        "processing": "处理中", "pending": "待处理",
    }
    review_status = [
        {"name": status_label_map.get(r.status, r.status), "value": r.cnt}
        for r in status_rows
    ]

    # --- recent activities (from MergeRequestReview only) ---
    def _time_ago(dt: datetime) -> str:
        elapsed = now - dt
        secs = elapsed.total_seconds()
        if secs < 60:
            return "刚刚"
        if secs < 3600:
            return f"{int(secs // 60)} 分钟前"
        if secs < 86400:
            return f"{int(secs // 3600)} 小时前"
        return f"{elapsed.days} 天前"

    review_status_type = {
        "completed": "success", "failed": "warning",
        "processing": "primary", "pending": "info",
    }
    review_title_label = {
        "completed": "审查已完成", "failed": "审查失败",
        "processing": "审查中", "pending": "待审查",
    }

    recent_reviews = (
        await db.execute(
            select(MergeRequestReview)
            .order_by(MergeRequestReview.created_at.desc())
            .limit(4)
        )
    ).scalars().all()

    activities = []
    for r in recent_reviews:
        activities.append({
            "review_id": r.id,
            "mr_iid": r.merge_request_iid,
            "mr_title": r.merge_request_title or "",
            "status": review_title_label.get(r.status, r.status),
            "type": review_status_type.get(r.status, "info"),
            "score": r.review_score,
            "model": r.llm_model or "",
            "project": r.project_name or "",
            "author": r.author_name or r.author_email or "",
            "branch": f"{r.source_branch} → {r.target_branch}" if r.source_branch else "",
            "time": _time_ago(r.created_at),
        })

    return {
        "review_trend": {"dates": dates, "reviews": reviews_data, "llm_calls": llm_data},
        "llm_distribution": llm_distribution,
        "review_status": review_status,
        "recent_activities": activities,
    }


@router.get("/reviews/")
async def list_reviews(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int | None = Query(default=None, ge=0),
    search: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    skip = offset if offset is not None else (page - 1) * limit

    base = select(MergeRequestReview)
    if search:
        pattern = f"%{search}%"
        base = base.where(
            MergeRequestReview.project_name.ilike(pattern)
            | MergeRequestReview.merge_request_title.ilike(pattern)
            | MergeRequestReview.author_name.ilike(pattern)
            | MergeRequestReview.source_branch.ilike(pattern)
        )

    count_stmt = select(MergeRequestReview.id).where(base.whereclause) if base.whereclause is not None else select(MergeRequestReview.id)
    count = len((await db.execute(count_stmt)).all())
    reviews = (
        await db.execute(
            base
            .order_by(MergeRequestReview.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
    ).scalars().all()
    return {
        "count": count,
        "total": count,
        "results": [MergeRequestReviewResponse.model_validate(item, from_attributes=True) for item in reviews],
    }


@router.get("/reviews/{review_id}/", response_model=MergeRequestReviewResponse)
async def get_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
) -> MergeRequestReviewResponse:
    review = await db.get(MergeRequestReview, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    return MergeRequestReviewResponse.model_validate(review, from_attributes=True)


@router.get("/reviews/{review_id}/findings/")
async def list_review_findings(
    review_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    review = await db.get(MergeRequestReview, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")

    findings = await materialize_review_findings_from_legacy(db, review=review)
    return {
        "count": len(findings),
        "results": [ReviewFindingResponse.model_validate(item, from_attributes=True) for item in findings],
    }


@router.get("/review-findings/", response_model=ReviewFindingWorkbenchListResponse)
async def list_review_findings_workbench(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    project_id: int | None = Query(default=None),
    severities: list[str] | None = Query(default=None),
    review_statuses: list[str] | None = Query(default=None),
    action_statuses: list[str] | None = Query(default=None),
    author: str | None = Query(default=None),
    start_at: datetime | None = Query(default=None),
    end_at: datetime | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ReviewFindingWorkbenchListResponse:
    skip = (page - 1) * limit
    normalized_review_statuses = (
        [item.strip().lower() for item in review_statuses if item and item.strip()]
        if review_statuses
        else []
    )
    await _materialize_legacy_findings_for_workbench(
        db,
        project_id=project_id,
        normalized_review_statuses=normalized_review_statuses,
        author=author,
    )

    latest_action_ranked = (
        select(
            ReviewFindingAction.id.label("id"),
            ReviewFindingAction.finding_id.label("finding_id"),
            ReviewFindingAction.action_type.label("action_type"),
            ReviewFindingAction.actor.label("actor"),
            ReviewFindingAction.note.label("note"),
            ReviewFindingAction.action_at.label("action_at"),
            func.row_number()
            .over(
                partition_by=ReviewFindingAction.finding_id,
                order_by=(ReviewFindingAction.action_at.desc(), ReviewFindingAction.id.desc()),
            )
            .label("rn"),
        )
    ).subquery("latest_action_ranked")
    latest_action = (
        select(
            latest_action_ranked.c.id,
            latest_action_ranked.c.finding_id,
            latest_action_ranked.c.action_type,
            latest_action_ranked.c.actor,
            latest_action_ranked.c.note,
            latest_action_ranked.c.action_at,
        )
        .where(latest_action_ranked.c.rn == 1)
    ).subquery("latest_action")

    base = (
        select(
            ReviewFinding,
            MergeRequestReview,
            latest_action.c.id.label("latest_action_id"),
            latest_action.c.action_type.label("latest_action_type"),
            latest_action.c.actor.label("latest_action_actor"),
            latest_action.c.note.label("latest_action_note"),
            latest_action.c.action_at.label("latest_action_at"),
        )
        .join(MergeRequestReview, MergeRequestReview.id == ReviewFinding.review_id)
        .outerjoin(latest_action, latest_action.c.finding_id == ReviewFinding.id)
    )

    if project_id is not None:
        base = base.where(MergeRequestReview.project_id == project_id)
    if severities:
        normalized_severities = [item.strip().lower() for item in severities if item and item.strip()]
        if normalized_severities:
            base = base.where(ReviewFinding.severity.in_(normalized_severities))
    if normalized_review_statuses:
        base = base.where(MergeRequestReview.status.in_(normalized_review_statuses))
    if author:
        pattern = f"%{author.strip()}%"
        base = base.where(
            or_(
                MergeRequestReview.author_name.ilike(pattern),
                MergeRequestReview.author_email.ilike(pattern),
            )
        )
    if start_at is not None:
        base = base.where(ReviewFinding.created_at >= start_at)
    if end_at is not None:
        base = base.where(ReviewFinding.created_at <= end_at)
    if action_statuses:
        normalized_action_statuses = [item.strip().lower() for item in action_statuses if item and item.strip()]
        invalid_statuses = sorted({item for item in normalized_action_statuses if item not in ALLOWED_ACTION_STATUSES})
        if invalid_statuses:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Invalid action_statuses: "
                    f"{', '.join(invalid_statuses)}. "
                    f"Allowed values: {', '.join(ALLOWED_ACTION_STATUSES)}."
                ),
            )
        action_types = [item for item in normalized_action_statuses if item in {"fixed", "ignored", "todo", "reopened"}]
        include_unprocessed = "unprocessed" in normalized_action_statuses
        status_filters = []
        if action_types:
            status_filters.append(latest_action.c.action_type.in_(action_types))
        if include_unprocessed:
            status_filters.append(latest_action.c.id.is_(None))
        if status_filters:
            base = base.where(or_(*status_filters))

    total = (
        await db.execute(
            select(func.count())
            .select_from(base.subquery())
        )
    ).scalar() or 0

    rows = (
        await db.execute(
            base
            .order_by(ReviewFinding.created_at.desc(), ReviewFinding.id.desc())
            .offset(skip)
            .limit(limit)
        )
    ).all()

    results: list[ReviewFindingWorkbenchItem] = []
    for finding, review, latest_action_id, latest_action_type, latest_action_actor, latest_action_note, latest_action_at in rows:
        review_meta = ReviewFindingWorkbenchReviewMeta(
            id=review.id,
            project_id=review.project_id,
            project_name=review.project_name,
            merge_request_iid=review.merge_request_iid,
            merge_request_title=review.merge_request_title,
            author_name=review.author_name,
            author_email=review.author_email,
            status=review.status,
            created_at=review.created_at,
        )
        latest_action_payload = (
            ReviewFindingActionResponse(
                id=latest_action_id,
                finding_id=finding.id,
                action_type=latest_action_type,
                actor=latest_action_actor,
                note=latest_action_note or "",
                action_at=latest_action_at,
            )
            if latest_action_id is not None
            else None
        )
        finding_payload = ReviewFindingResponse.model_validate(finding, from_attributes=True).model_dump()
        finding_payload["issue_id"] = finding.issue_id
        results.append(
            ReviewFindingWorkbenchItem(
                **finding_payload,
                review=review_meta,
                latest_action=latest_action_payload,
                action_status=str(latest_action_type or "unprocessed"),
            )
        )

    return ReviewFindingWorkbenchListResponse(count=len(results), total=int(total), results=results)


@router.post("/review-findings/{finding_id}/actions/", response_model=ReviewFindingActionResponse)
async def create_review_finding_action(
    finding_id: int,
    payload: ReviewFindingActionCreate,
    db: AsyncSession = Depends(get_db),
) -> ReviewFindingActionResponse:
    finding = await db.get(ReviewFinding, finding_id)
    if finding is None:
        raise HTTPException(status_code=404, detail="Review finding not found.")

    action = ReviewFindingAction(
        finding_id=finding_id,
        action_type=payload.action_type,
        actor=payload.actor,
        note=payload.note,
    )
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return ReviewFindingActionResponse.model_validate(action, from_attributes=True)


@router.post("/review-findings/actions/batch/", response_model=ReviewFindingBatchActionResponse)
async def batch_create_review_finding_actions(
    payload: ReviewFindingBatchActionCreate,
    db: AsyncSession = Depends(get_db),
) -> ReviewFindingBatchActionResponse:
    finding_ids: list[int] = []
    seen: set[int] = set()
    for finding_id in payload.finding_ids:
        if finding_id in seen:
            continue
        seen.add(finding_id)
        finding_ids.append(finding_id)

    existing_ids = set(
        (
            await db.execute(
                select(ReviewFinding.id).where(ReviewFinding.id.in_(finding_ids))
            )
        ).scalars().all()
    )
    actions: list[ReviewFindingAction] = []
    failed_ids: list[int] = []
    for finding_id in finding_ids:
        if finding_id not in existing_ids:
            failed_ids.append(finding_id)
            continue
        actions.append(
            ReviewFindingAction(
                finding_id=finding_id,
                action_type=payload.action_type,
                actor=payload.actor,
                note=payload.note,
            )
        )

    if actions:
        db.add_all(actions)
        await db.commit()

    return ReviewFindingBatchActionResponse(
        success_count=len(actions),
        failed_count=len(failed_ids),
        failed_ids=failed_ids,
    )


@router.get("/review-findings/stats/", response_model=ReviewFindingStatsResponse)
async def get_review_findings_stats(
    days: int = Query(default=30, ge=1, le=365),
    project_id: int | None = Query(default=None),
    owner: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ReviewFindingStatsResponse:
    start_time = datetime.now() - timedelta(days=days)
    owner_display_expr = func.coalesce(
        ReviewFinding.owner_name,
        ReviewFinding.owner_email,
        ReviewFinding.owner,
        "unknown",
    )

    filters = [ReviewFinding.created_at >= start_time]
    if project_id is not None:
        filters.append(MergeRequestReview.project_id == project_id)
    if owner:
        filters.append(
            or_(
                ReviewFinding.owner_name == owner,
                ReviewFinding.owner_email == owner,
                ReviewFinding.owner == owner,
            )
        )

    total_findings = (
        await db.execute(
            select(func.count())
            .select_from(ReviewFinding)
            .join(MergeRequestReview, MergeRequestReview.id == ReviewFinding.review_id)
            .where(*filters)
        )
    ).scalar() or 0

    by_category_rows = (
        await db.execute(
            select(ReviewFinding.category, func.count().label("cnt"))
            .select_from(ReviewFinding)
            .join(MergeRequestReview, MergeRequestReview.id == ReviewFinding.review_id)
            .where(*filters)
            .group_by(ReviewFinding.category)
            .order_by(func.count().desc())
        )
    ).all()
    by_severity_rows = (
        await db.execute(
            select(ReviewFinding.severity, func.count().label("cnt"))
            .select_from(ReviewFinding)
            .join(MergeRequestReview, MergeRequestReview.id == ReviewFinding.review_id)
            .where(*filters)
            .group_by(ReviewFinding.severity)
            .order_by(func.count().desc())
        )
    ).all()
    by_owner_rows = (
        await db.execute(
            select(owner_display_expr.label("owner_display"), func.count().label("cnt"))
            .select_from(ReviewFinding)
            .join(MergeRequestReview, MergeRequestReview.id == ReviewFinding.review_id)
            .where(*filters)
            .group_by(owner_display_expr)
            .order_by(func.count().desc())
        )
    ).all()
    trend_rows = (
        await db.execute(
            select(func.date(ReviewFinding.created_at).label("day"), func.count().label("cnt"))
            .select_from(ReviewFinding)
            .join(MergeRequestReview, MergeRequestReview.id == ReviewFinding.review_id)
            .where(*filters)
            .group_by(func.date(ReviewFinding.created_at))
            .order_by(func.date(ReviewFinding.created_at))
        )
    ).all()

    daily_trend = [{"date": str(row.day), "value": int(row.cnt or 0)} for row in trend_rows]
    return ReviewFindingStatsResponse(
        total_findings=int(total_findings),
        by_category=_to_bucket_rows(by_category_rows),
        by_severity=_to_bucket_rows(by_severity_rows),
        by_owner=_to_bucket_rows(by_owner_rows),
        daily_trend=daily_trend,
    )


@router.get("/logs/")
async def list_logs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int | None = Query(default=None, ge=0),
    search: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    skip = offset if offset is not None else (page - 1) * limit

    base = select(WebhookLog)
    if search:
        pattern = f"%{search}%"
        base = base.where(
            WebhookLog.event_type.ilike(pattern)
            | WebhookLog.project_name.ilike(pattern)
        )

    count_stmt = select(WebhookLog.id).where(base.whereclause) if base.whereclause is not None else select(WebhookLog.id)
    count = len((await db.execute(count_stmt)).all())
    logs = (
        await db.execute(
            base
            .order_by(WebhookLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
    ).scalars().all()
    return {
        "count": count,
        "total": count,
        "results": [WebhookLogResponse.model_validate(item, from_attributes=True) for item in logs],
    }
