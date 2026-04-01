from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.deps import get_db
from app.models import AuthUser, ProjectIgnoreStrategy
from app.schemas.project import (
    ProjectIgnoreStrategyDisableAllRequest,
    ProjectIgnoreStrategyDisableAllResponse,
    ProjectIgnoreStrategyDisableRequest,
    ProjectIgnoreStrategyListResponse,
    ProjectIgnoreStrategyResponse,
)
from app.services.reporting import (
    generate_developer_weekly_cards,
    generate_developer_weekly_report,
    generate_ignore_strategy_weekly_report,
    generate_mr_feedback_weekly_report,
)
from app.services.reporting.developer_weekly_snapshot import (
    get_cached_developer_weekly_cards,
    get_cached_developer_weekly_report,
)

router = APIRouter()
_STATUS_ACTIVE = "active"
_STATUS_EXPIRED = "expired"
_STATUS_DISABLED = "disabled"
_ALLOWED_STRATEGY_STATUSES = {_STATUS_ACTIVE, _STATUS_EXPIRED, _STATUS_DISABLED}


def _normalize_status_filters(raw_statuses: list[str] | None) -> list[str]:
    if not raw_statuses:
        return []
    normalized = [str(item or "").strip().lower() for item in raw_statuses]
    normalized = [item for item in normalized if item]
    invalid = [item for item in normalized if item not in _ALLOWED_STRATEGY_STATUSES]
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid statuses: {invalid}. Allowed: {sorted(_ALLOWED_STRATEGY_STATUSES)}",
        )
    unique: list[str] = []
    for item in normalized:
        if item not in unique:
            unique.append(item)
    return unique


def _resolve_disable_reason(raw: str, *, actor_username: str) -> str:
    normalized = str(raw or "").strip()
    if normalized:
        return normalized[:1000]
    actor = str(actor_username or "").strip() or "unknown"
    return f"Disabled manually by {actor}"[:1000]


@router.get("/reports/mr-feedback/weekly/")
async def get_mr_feedback_weekly_report(
    project_id: int | None = Query(default=None),
    anchor_date: date | None = Query(default=None, description="统计周内任意日期，默认今天"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await generate_mr_feedback_weekly_report(
        db,
        project_id=project_id,
        anchor_date=anchor_date,
    )


@router.get("/reports/developers/weekly/")
async def get_developer_weekly_report(
    owner: str | None = Query(default=None),
    owner_email: str | None = Query(default=None),
    include_statuses: list[str] | None = Query(default=None),
    anchor_date: date | None = Query(default=None, description="统计周内任意日期，默认今天"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    cached = await get_cached_developer_weekly_report(
        db,
        owner=owner,
        owner_email=owner_email,
        include_statuses=include_statuses,
        anchor_date=anchor_date,
    )
    if cached is not None:
        return cached
    return await generate_developer_weekly_report(
        db,
        owner=owner,
        owner_email=owner_email,
        include_statuses=include_statuses,
        anchor_date=anchor_date,
    )


@router.get("/reports/developers/weekly/cards/")
async def get_developer_weekly_cards(
    anchor_date: date | None = Query(default=None, description="统计周内任意日期，默认今天"),
    limit: int = Query(default=30, ge=1, le=200),
    include_statuses: list[str] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    cached = await get_cached_developer_weekly_cards(
        db,
        anchor_date=anchor_date,
        limit=limit,
        include_statuses=include_statuses,
    )
    if cached is not None:
        return cached
    return await generate_developer_weekly_cards(
        db,
        anchor_date=anchor_date,
        limit=limit,
        include_statuses=include_statuses,
    )


@router.get("/reports/ignore-strategies/weekly/")
async def get_ignore_strategy_weekly_report(
    project_id: int | None = Query(default=None),
    anchor_date: date | None = Query(default=None, description="统计窗口内任意日期，默认今天"),
    apply_changes: bool = Query(default=False, description="是否将符合条件策略写入并生效"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await generate_ignore_strategy_weekly_report(
        db,
        project_id=project_id,
        anchor_date=anchor_date,
        apply_changes=apply_changes,
    )


@router.get("/reports/ignore-strategies/", response_model=ProjectIgnoreStrategyListResponse)
async def list_project_ignore_strategies(
    project_id: int = Query(..., ge=1),
    statuses: list[str] | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ProjectIgnoreStrategyListResponse:
    normalized_statuses = _normalize_status_filters(statuses)
    stmt = (
        select(ProjectIgnoreStrategy)
        .where(ProjectIgnoreStrategy.project_id == project_id)
        .order_by(
            case(
                (ProjectIgnoreStrategy.status == _STATUS_ACTIVE, 0),
                (ProjectIgnoreStrategy.status == _STATUS_EXPIRED, 1),
                else_=2,
            ),
            ProjectIgnoreStrategy.confidence_score.desc(),
            ProjectIgnoreStrategy.sample_count_4w.desc(),
            ProjectIgnoreStrategy.id.desc(),
        )
    )
    if normalized_statuses:
        stmt = stmt.where(ProjectIgnoreStrategy.status.in_(normalized_statuses))
    rows = (await db.execute(stmt)).scalars().all()
    return ProjectIgnoreStrategyListResponse(
        count=len(rows),
        results=[ProjectIgnoreStrategyResponse.model_validate(row, from_attributes=True) for row in rows],
    )


@router.patch(
    "/reports/ignore-strategies/{strategy_id}/disable/",
    response_model=ProjectIgnoreStrategyResponse,
)
async def disable_project_ignore_strategy(
    strategy_id: int,
    payload: ProjectIgnoreStrategyDisableRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> ProjectIgnoreStrategyResponse:
    strategy = await db.get(ProjectIgnoreStrategy, strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail="Ignore strategy not found.")

    if strategy.status != _STATUS_DISABLED:
        now = datetime.now(UTC).replace(tzinfo=None)
        strategy.status = _STATUS_DISABLED
        strategy.disabled_at = now
        strategy.disabled_reason = _resolve_disable_reason(
            payload.reason if payload is not None else "",
            actor_username=current_user.username,
        )
        await db.commit()
        await db.refresh(strategy)

    return ProjectIgnoreStrategyResponse.model_validate(strategy, from_attributes=True)


@router.post(
    "/reports/ignore-strategies/disable-all/",
    response_model=ProjectIgnoreStrategyDisableAllResponse,
)
async def disable_all_project_ignore_strategies(
    payload: ProjectIgnoreStrategyDisableAllRequest,
    db: AsyncSession = Depends(get_db),
    current_user: AuthUser = Depends(get_current_user),
) -> ProjectIgnoreStrategyDisableAllResponse:
    rows = (
        await db.execute(
            select(ProjectIgnoreStrategy).where(
                ProjectIgnoreStrategy.project_id == payload.project_id,
                ProjectIgnoreStrategy.status != _STATUS_DISABLED,
            )
        )
    ).scalars().all()

    now = datetime.now(UTC).replace(tzinfo=None)
    reason = _resolve_disable_reason(payload.reason, actor_username=current_user.username)
    for row in rows:
        row.status = _STATUS_DISABLED
        row.disabled_at = now
        row.disabled_reason = reason

    if rows:
        await db.commit()

    return ProjectIgnoreStrategyDisableAllResponse(
        project_id=payload.project_id,
        disabled_count=len(rows),
        disabled_at=now if rows else None,
    )
