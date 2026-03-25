from __future__ import annotations

from collections import Counter
import json
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import MRFeedbackRecord, MergeRequestReview, ReviewFinding, SystemConfig

_ALLOWED_SUMMARY_STATUSES = {"open", "ignored", "reopened"}
_DEFAULT_INCLUDE_STATUSES = ["open", "reopened"]
_STATUS_ORDER = ["open", "ignored", "reopened"]
_DEVELOPER_WEEKLY_INCLUDE_STATUSES_CONFIG_KEY = "reports.developer_weekly.include_statuses"


def _build_week_window(anchor_date: date | None, tz_name: str) -> tuple[date, date, datetime, datetime]:
    tz = ZoneInfo(tz_name)
    today = datetime.now(tz).date() if anchor_date is None else anchor_date
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    start_dt = datetime.combine(week_start, datetime.min.time())
    end_dt_exclusive = datetime.combine(week_end + timedelta(days=1), datetime.min.time())
    return week_start, week_end, start_dt, end_dt_exclusive


def _build_ai_summary(
    *,
    owner_name: str,
    total_findings: int,
    top_category: str,
    top_severity: str,
    ignore_count: int,
    reopen_count: int,
) -> str:
    if total_findings <= 0:
        return f"{owner_name} 本周未发现结构化问题，建议保持当前提交与自检节奏。"

    base = (
        f"{owner_name} 本周共出现 {total_findings} 条问题，"
        f"主要集中在「{top_category}」，严重度以「{top_severity}」为主。"
    )
    if ignore_count + reopen_count <= 0:
        return base + " 当前暂无对应回收记录，建议结合 MR 评论做一次主动复盘。"
    if ignore_count >= reopen_count:
        return base + " 回收中以忽略为主，建议优先补齐可快速修复的同类问题。"
    return base + " 回收中重新跟踪比例较高，建议将相关检查项固化到提交流程。"


def _build_gap_checklist(category_counter: Counter[str], severity_counter: Counter[str]) -> list[str]:
    checklist: list[str] = []
    top_categories = [name for name, _ in category_counter.most_common(2)]
    severity = "medium"
    if severity_counter:
        severity = severity_counter.most_common(1)[0][0]

    if "security" in top_categories or "安全" in top_categories:
        checklist.append("安全类问题偏多：提交前补充鉴权/输入校验自查。")
    if "quality" in top_categories or "质量" in top_categories:
        checklist.append("质量类问题偏多：提交前执行关键路径单测并检查边界分支。")
    if "style" in top_categories or "风格" in top_categories:
        checklist.append("风格类问题偏多：合并前统一跑 lint/format，减少可自动修复噪音。")
    if severity in {"critical", "high"}:
        checklist.append("高严重度问题存在：建议合并前补一轮同伴复查。")

    if not checklist:
        checklist.append("本周问题分布较均衡：建议继续保持提交前自检清单。")
    return checklist


def _normalize_include_statuses(raw: Any) -> list[str]:
    items: list[Any]
    if isinstance(raw, (list, tuple, set)):
        items = list(raw)
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            items = parsed
        else:
            items = [item.strip() for item in text.split(",")]
    else:
        return []

    normalized = {str(item or "").strip().lower() for item in items}
    return [status for status in _STATUS_ORDER if status in normalized and status in _ALLOWED_SUMMARY_STATUSES]


async def _resolve_include_statuses(
    db: AsyncSession,
    *,
    include_statuses: list[str] | None = None,
) -> list[str]:
    normalized_override = _normalize_include_statuses(include_statuses or [])
    if normalized_override:
        return normalized_override

    config_value = (
        await db.execute(
            select(SystemConfig.value)
            .where(SystemConfig.key == _DEVELOPER_WEEKLY_INCLUDE_STATUSES_CONFIG_KEY)
            .limit(1)
        )
    ).scalar_one_or_none()
    normalized_config = _normalize_include_statuses(config_value)
    if normalized_config:
        return normalized_config

    return list(_DEFAULT_INCLUDE_STATUSES)


def _build_issue_key(project_id: Any, merge_request_iid: Any, issue_id: Any) -> tuple[int, int, str] | None:
    if project_id is None or merge_request_iid is None:
        return None
    issue_text = str(issue_id or "").strip()
    if not issue_text:
        return None
    return int(project_id), int(merge_request_iid), issue_text


async def _resolve_issue_status_map(
    db: AsyncSession,
    *,
    issue_keys: set[tuple[int, int, str]],
    end_dt_exclusive: datetime,
) -> dict[tuple[int, int, str], str]:
    if not issue_keys:
        return {}

    feedback_rows = (
        await db.execute(
            select(
                MRFeedbackRecord.project_id,
                MRFeedbackRecord.merge_request_iid,
                MRFeedbackRecord.issue_id,
                MRFeedbackRecord.action,
            )
            .where(
                MRFeedbackRecord.created_at < end_dt_exclusive,
                MRFeedbackRecord.issue_id != "",
            )
            .order_by(MRFeedbackRecord.created_at.desc(), MRFeedbackRecord.id.desc())
        )
    ).all()

    status_map: dict[tuple[int, int, str], str] = {}
    for project_id, merge_request_iid, issue_id, action in feedback_rows:
        issue_key = _build_issue_key(project_id, merge_request_iid, issue_id)
        if issue_key is None or issue_key not in issue_keys or issue_key in status_map:
            continue
        if action == "ignore":
            status_map[issue_key] = "ignored"
        elif action == "reopen":
            status_map[issue_key] = "reopened"
    return status_map


def _resolve_finding_status(
    *,
    row: Any,
    issue_status_map: dict[tuple[int, int, str], str],
) -> str:
    issue_key = _build_issue_key(row.project_id, row.merge_request_iid, row.issue_id)
    if issue_key is None:
        return "open"
    return issue_status_map.get(issue_key, "open")


async def generate_developer_weekly_cards(
    db: AsyncSession,
    *,
    anchor_date: date | None = None,
    limit: int = 30,
    include_statuses: list[str] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    week_start, week_end, start_dt, end_dt_exclusive = _build_week_window(anchor_date, settings.TIMEZONE)
    normalized_include_statuses = await _resolve_include_statuses(
        db,
        include_statuses=include_statuses,
    )
    include_statuses_set = set(normalized_include_statuses)

    finding_rows = (
        await db.execute(
            select(
                ReviewFinding.review_id,
                ReviewFinding.issue_id,
                ReviewFinding.category,
                ReviewFinding.severity,
                ReviewFinding.owner_name,
                ReviewFinding.owner_email,
                MergeRequestReview.project_id,
                MergeRequestReview.merge_request_iid,
            )
            .join(MergeRequestReview, MergeRequestReview.id == ReviewFinding.review_id)
            .where(
                ReviewFinding.created_at >= start_dt,
                ReviewFinding.created_at < end_dt_exclusive,
                ReviewFinding.owner_name.is_not(None),
                ReviewFinding.owner_name != "",
            )
        )
    ).all()

    issue_keys = {
        issue_key
        for row in finding_rows
        if (issue_key := _build_issue_key(row.project_id, row.merge_request_iid, row.issue_id)) is not None
    }
    issue_status_map = await _resolve_issue_status_map(
        db,
        issue_keys=issue_keys,
        end_dt_exclusive=end_dt_exclusive,
    )

    owner_rows: dict[str, dict[str, Any]] = {}
    for row in finding_rows:
        owner = str(row.owner_name or "").strip()
        if not owner:
            continue
        profile = owner_rows.setdefault(
            owner,
            {
                "owner": owner,
                "owner_email": str(row.owner_email or "").strip() or None,
                "raw_finding_count": 0,
                "finding_count": 0,
                "review_ids": set(),
                "category_counter": Counter(),
                "severity_counter": Counter(),
                "mr_keys": set(),
            },
        )
        profile["raw_finding_count"] += 1
        if row.project_id is not None and row.merge_request_iid is not None:
            profile["mr_keys"].add((int(row.project_id), int(row.merge_request_iid)))
        if profile["owner_email"] is None and row.owner_email:
            profile["owner_email"] = str(row.owner_email).strip()
        finding_status = _resolve_finding_status(row=row, issue_status_map=issue_status_map)
        if finding_status not in include_statuses_set:
            continue
        profile["finding_count"] += 1
        if row.review_id is not None:
            profile["review_ids"].add(int(row.review_id))
        profile["category_counter"][str(row.category or "unknown")] += 1
        profile["severity_counter"][str(row.severity or "medium")] += 1

    feedback_rows = (
        await db.execute(
            select(MRFeedbackRecord.project_id, MRFeedbackRecord.merge_request_iid, MRFeedbackRecord.action)
            .where(
                MRFeedbackRecord.created_at >= start_dt,
                MRFeedbackRecord.created_at < end_dt_exclusive,
            )
        )
    ).all()

    cards: list[dict[str, Any]] = []
    for owner, profile in owner_rows.items():
        included_findings = int(profile["finding_count"])
        raw_findings = int(profile["raw_finding_count"])
        if included_findings <= 0:
            continue
        ignore_actions = 0
        reopen_actions = 0
        mr_keys = profile["mr_keys"]
        for project_id, merge_request_iid, action in feedback_rows:
            if (int(project_id), int(merge_request_iid)) not in mr_keys:
                continue
            if action == "ignore":
                ignore_actions += 1
            elif action == "reopen":
                reopen_actions += 1

        category_counter: Counter[str] = profile["category_counter"]
        severity_counter: Counter[str] = profile["severity_counter"]
        top_category = category_counter.most_common(1)[0][0] if category_counter else "无"
        top_severity = severity_counter.most_common(1)[0][0] if severity_counter else "无"
        ai_summary = _build_ai_summary(
            owner_name=owner,
            total_findings=included_findings,
            top_category=top_category,
            top_severity=top_severity,
            ignore_count=ignore_actions,
            reopen_count=reopen_actions,
        )
        gap_checklist = _build_gap_checklist(category_counter, severity_counter)
        total_actions = ignore_actions + reopen_actions
        cards.append(
            {
                "owner": owner,
                "owner_email": profile["owner_email"],
                "total_findings": included_findings,
                "raw_total_findings": raw_findings,
                "excluded_findings": max(0, raw_findings - included_findings),
                "total_reviews": len(profile["review_ids"]),
                "ignore_actions": ignore_actions,
                "reopen_actions": reopen_actions,
                "ignore_rate": round(ignore_actions / total_actions, 4) if total_actions > 0 else 0.0,
                "top_category": top_category,
                "top_severity": top_severity,
                "summary_excerpt": ai_summary[:120],
                "improvement_focus": gap_checklist[0] if gap_checklist else "建议保持当前自检节奏。",
            }
        )

    cards.sort(key=lambda item: (-int(item["total_findings"]), str(item["owner"])))
    normalized_limit = max(1, min(int(limit or 30), 200))
    results = cards[:normalized_limit]

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "include_statuses": normalized_include_statuses,
        "count": len(results),
        "results": results,
        "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds"),
        "source": "live",
    }


async def generate_developer_weekly_report(
    db: AsyncSession,
    *,
    owner: str | None = None,
    owner_email: str | None = None,
    anchor_date: date | None = None,
    include_statuses: list[str] | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    week_start, week_end, start_dt, end_dt_exclusive = _build_week_window(anchor_date, settings.TIMEZONE)
    normalized_include_statuses = await _resolve_include_statuses(
        db,
        include_statuses=include_statuses,
    )
    include_statuses_set = set(normalized_include_statuses)

    owners_rows = (
        await db.execute(
            select(ReviewFinding.owner_name)
            .where(
                ReviewFinding.created_at >= start_dt,
                ReviewFinding.created_at < end_dt_exclusive,
                ReviewFinding.owner_name.is_not(None),
                ReviewFinding.owner_name != "",
            )
            .group_by(ReviewFinding.owner_name)
            .order_by(func.count(ReviewFinding.id).desc(), ReviewFinding.owner_name.asc())
        )
    ).all()
    available_owners = [str(item[0]) for item in owners_rows if item and item[0]]

    stmt = (
        select(
            ReviewFinding.id,
            ReviewFinding.review_id,
            ReviewFinding.issue_id,
            ReviewFinding.category,
            ReviewFinding.severity,
            ReviewFinding.file_path,
            ReviewFinding.owner_name,
            ReviewFinding.owner_email,
            MergeRequestReview.project_id,
            MergeRequestReview.project_name,
            MergeRequestReview.merge_request_iid,
        )
        .join(MergeRequestReview, MergeRequestReview.id == ReviewFinding.review_id)
        .where(
            ReviewFinding.created_at >= start_dt,
            ReviewFinding.created_at < end_dt_exclusive,
        )
    )
    normalized_owner = str(owner or "").strip()
    normalized_owner_email = str(owner_email or "").strip()
    if normalized_owner:
        stmt = stmt.where(ReviewFinding.owner_name == normalized_owner)
    if normalized_owner_email:
        stmt = stmt.where(ReviewFinding.owner_email == normalized_owner_email)

    finding_rows = (await db.execute(stmt)).all()

    issue_keys = {
        issue_key
        for row in finding_rows
        if (issue_key := _build_issue_key(row.project_id, row.merge_request_iid, row.issue_id)) is not None
    }
    issue_status_map = await _resolve_issue_status_map(
        db,
        issue_keys=issue_keys,
        end_dt_exclusive=end_dt_exclusive,
    )
    filtered_finding_rows = [
        row
        for row in finding_rows
        if _resolve_finding_status(row=row, issue_status_map=issue_status_map) in include_statuses_set
    ]

    raw_total_findings = len(finding_rows)
    total_findings = len(filtered_finding_rows)
    review_ids = {int(row.review_id) for row in filtered_finding_rows if row.review_id is not None}
    project_counter = Counter(str(row.project_name or f"项目 {row.project_id}") for row in filtered_finding_rows)
    category_counter = Counter(str(row.category or "unknown") for row in filtered_finding_rows)
    severity_counter = Counter(str(row.severity or "medium") for row in filtered_finding_rows)
    file_counter = Counter(str(row.file_path or "unknown") for row in filtered_finding_rows if row.file_path)

    touched_mr_keys = {
        (int(row.project_id), int(row.merge_request_iid))
        for row in finding_rows
        if row.project_id is not None and row.merge_request_iid is not None
    }

    feedback_rows = (
        await db.execute(
            select(MRFeedbackRecord.project_id, MRFeedbackRecord.merge_request_iid, MRFeedbackRecord.action)
            .where(
                MRFeedbackRecord.created_at >= start_dt,
                MRFeedbackRecord.created_at < end_dt_exclusive,
            )
        )
    ).all()

    ignore_count = 0
    reopen_count = 0
    for project_id, merge_request_iid, action in feedback_rows:
        key = (int(project_id), int(merge_request_iid))
        if (normalized_owner or normalized_owner_email) and key not in touched_mr_keys:
            continue
        if action == "ignore":
            ignore_count += 1
        elif action == "reopen":
            reopen_count += 1

    actor = normalized_owner or (available_owners[0] if available_owners else "该成员")
    top_category = category_counter.most_common(1)[0][0] if category_counter else "无"
    top_severity = severity_counter.most_common(1)[0][0] if severity_counter else "无"

    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "include_statuses": normalized_include_statuses,
        "owner": normalized_owner or None,
        "owner_email": normalized_owner_email or None,
        "available_owners": available_owners,
        "summary": {
            "total_findings": total_findings,
            "raw_total_findings": raw_total_findings,
            "excluded_findings": max(0, raw_total_findings - total_findings),
            "total_reviews": len(review_ids),
            "ignore_actions": ignore_count,
            "reopen_actions": reopen_count,
            "ignore_rate": round(ignore_count / (ignore_count + reopen_count), 4)
            if (ignore_count + reopen_count) > 0
            else 0.0,
        },
        "by_category": [{"name": name, "value": int(value)} for name, value in category_counter.most_common(5)],
        "by_severity": [{"name": name, "value": int(value)} for name, value in severity_counter.most_common()],
        "top_files": [{"name": name, "value": int(value)} for name, value in file_counter.most_common(5)],
        "projects": [{"name": name, "value": int(value)} for name, value in project_counter.most_common()],
        "ai_summary": _build_ai_summary(
            owner_name=actor,
            total_findings=total_findings,
            top_category=top_category,
            top_severity=top_severity,
            ignore_count=ignore_count,
            reopen_count=reopen_count,
        ),
        "gap_checklist": _build_gap_checklist(category_counter, severity_counter),
        "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds"),
        "source": "heuristic",
    }
