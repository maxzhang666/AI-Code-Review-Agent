from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_db
from app.models import MRFeedbackRecord
from app.schemas.mr_feedback import MRFeedbackRecordResponse

router = APIRouter()


@router.get("/mr-feedback/records/")
async def list_mr_feedback_records(
    page: int = Query(default=1, ge=1),
    project_id: int | None = Query(default=None),
    action: str | None = Query(default=None),
    issue_id: str | None = Query(default=None),
    days: int | None = Query(default=None, ge=1),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    settings = get_settings()
    page_size = settings.PAGE_SIZE
    offset = (page - 1) * page_size

    conditions = []
    if project_id is not None:
        conditions.append(MRFeedbackRecord.project_id == project_id)
    if action is not None:
        conditions.append(MRFeedbackRecord.action == action)
    if issue_id is not None:
        conditions.append(MRFeedbackRecord.issue_id == issue_id)
    if days is not None:
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)
        conditions.append(MRFeedbackRecord.created_at >= cutoff)

    count_stmt = select(MRFeedbackRecord.id)
    list_stmt = (
        select(MRFeedbackRecord)
        .order_by(MRFeedbackRecord.created_at.desc(), MRFeedbackRecord.id.desc())
        .offset(offset)
        .limit(page_size)
    )
    if conditions:
        count_stmt = count_stmt.where(*conditions)
        list_stmt = list_stmt.where(*conditions)

    count = len((await db.execute(count_stmt)).all())
    rows = (await db.execute(list_stmt)).scalars().all()

    return {
        "count": count,
        "results": [MRFeedbackRecordResponse.model_validate(item, from_attributes=True) for item in rows],
    }

