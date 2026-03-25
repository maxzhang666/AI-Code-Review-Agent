from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.services.reporting import (
    generate_developer_weekly_cards,
    generate_developer_weekly_report,
    generate_mr_feedback_weekly_report,
)
from app.services.reporting.developer_weekly_snapshot import (
    get_cached_developer_weekly_cards,
    get_cached_developer_weekly_report,
)

router = APIRouter()


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
