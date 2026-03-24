from __future__ import annotations

import pytest

from app.models import SystemConfig
from app.queue.tasks import _resolve_review_code_snippet_source


@pytest.mark.asyncio
async def test_resolve_review_code_snippet_source_uses_system_config(db_session) -> None:
    db_session.add(SystemConfig(key="review.code_snippet_source", value="llm"))
    await db_session.commit()

    value = await _resolve_review_code_snippet_source(
        db_session,
        default_source="line",
    )

    assert value == "llm"


@pytest.mark.asyncio
async def test_resolve_review_code_snippet_source_falls_back_to_default_when_invalid(
    db_session,
) -> None:
    db_session.add(SystemConfig(key="review.code_snippet_source", value="unsupported"))
    await db_session.commit()

    value = await _resolve_review_code_snippet_source(
        db_session,
        default_source="llm",
    )

    assert value == "llm"


@pytest.mark.asyncio
async def test_resolve_review_code_snippet_source_normalizes_default(db_session) -> None:
    value = await _resolve_review_code_snippet_source(
        db_session,
        default_source="invalid-default",
    )

    assert value == "line"
