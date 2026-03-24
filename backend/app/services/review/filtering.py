from __future__ import annotations

import fnmatch
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import Project


async def load_project_config(
    settings: Settings,
    project_id: int | None,
    db: AsyncSession,
) -> tuple[list[str], list[str]]:
    default_exclude = list(settings.EXCLUDE_FILE_TYPES)
    default_ignore = list(settings.IGNORE_FILE_TYPES)
    if project_id is None:
        return default_exclude, default_ignore

    stmt = select(Project).where(Project.project_id == project_id).limit(1)
    project = (await db.execute(stmt)).scalars().first()
    if project is None:
        return default_exclude, default_ignore

    exclude_file_types = (
        default_exclude
        if project.exclude_file_types is None
        else list(project.exclude_file_types)
    )
    ignore_patterns = (
        default_ignore
        if project.ignore_file_patterns is None
        else list(project.ignore_file_patterns)
    )
    return exclude_file_types, ignore_patterns


async def filter_changes(
    changes: list[dict[str, Any]],
    exclude_file_types: list[str],
    ignore_patterns: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    deleted_file_count = 0
    renamed_without_diff_count = 0
    excluded_by_type_count = 0
    ignored_by_pattern_count = 0
    excluded_by_type_sample: list[str] = []
    ignored_by_pattern_sample: list[str] = []
    for change in changes:
        if change.get("deleted_file"):
            deleted_file_count += 1
            continue
        if change.get("renamed_file") and not change.get("diff"):
            renamed_without_diff_count += 1
            continue

        file_path = str(change.get("new_path") or change.get("old_path") or "")
        if not file_path:
            continue

        matched_type = await matched_excluded_type(file_path, exclude_file_types)
        if matched_type is not None:
            excluded_by_type_count += 1
            if len(excluded_by_type_sample) < 5:
                excluded_by_type_sample.append(file_path)
            continue
        matched_pattern = await matched_ignore_pattern(file_path, ignore_patterns)
        if matched_pattern is not None:
            ignored_by_pattern_count += 1
            if len(ignored_by_pattern_sample) < 5:
                ignored_by_pattern_sample.append(file_path)
            continue

        filtered.append(change)
    raw_file_count = len(changes)
    filtered_file_count = len(filtered)
    summary = {
        "raw_file_count": raw_file_count,
        "filtered_file_count": filtered_file_count,
        "removed_file_count": raw_file_count - filtered_file_count,
        "excluded_by_type_count": excluded_by_type_count,
        "ignored_by_pattern_count": ignored_by_pattern_count,
        "deleted_file_count": deleted_file_count,
        "renamed_without_diff_count": renamed_without_diff_count,
        "excluded_by_type_sample": excluded_by_type_sample,
        "ignored_by_pattern_sample": ignored_by_pattern_sample,
    }
    return filtered, summary


async def matched_excluded_type(
    file_path: str,
    exclude_file_types: list[str],
) -> str | None:
    normalized_path = file_path.lower()
    for file_type in exclude_file_types:
        suffix = str(file_type).strip().lower()
        if suffix and normalized_path.endswith(suffix):
            return suffix
    return None


async def matched_ignore_pattern(
    file_path: str,
    ignore_patterns: list[str],
) -> str | None:
    normalized_path = file_path.strip()
    for pattern in ignore_patterns:
        item = str(pattern).strip()
        if not item:
            continue
        if item in normalized_path:
            return item
        if fnmatch.fnmatch(normalized_path, item):
            return item
    return None
