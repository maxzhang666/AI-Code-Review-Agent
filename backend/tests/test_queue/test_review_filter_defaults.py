from __future__ import annotations

import pytest

from app.config import get_settings
from app.models import Project
from app.services.review import ReviewService


def test_default_exclude_does_not_contain_common_source_extensions() -> None:
    settings = get_settings()
    assert ".java" not in settings.EXCLUDE_FILE_TYPES
    assert ".py" not in settings.EXCLUDE_FILE_TYPES
    assert ".vue" not in settings.EXCLUDE_FILE_TYPES
    assert ".go" not in settings.EXCLUDE_FILE_TYPES
    assert ".c" not in settings.EXCLUDE_FILE_TYPES
    assert ".cpp" not in settings.EXCLUDE_FILE_TYPES


@pytest.mark.asyncio
async def test_project_empty_filter_lists_should_not_fallback_to_defaults(db_session) -> None:
    project = Project(
        project_id=4001,
        project_name="empty-filter-demo",
        project_path="group/empty-filter-demo",
        project_url="https://gitlab.example.com/group/empty-filter-demo.git",
        namespace="group",
        review_enabled=True,
        exclude_file_types=[],
        ignore_file_patterns=[],
    )
    db_session.add(project)
    await db_session.commit()

    service = ReviewService(request_id="req-empty-filter")
    exclude_file_types, ignore_patterns = await service._load_project_config(project.project_id, db_session)

    assert exclude_file_types == []
    assert ignore_patterns == []

