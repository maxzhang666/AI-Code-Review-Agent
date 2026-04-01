from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import MergeRequestReview, ProjectIgnoreStrategy, ReviewFinding, ReviewFindingAction

_IGNORED_ACTION_TYPE = "ignored"
_STATUS_ACTIVE = "active"
_STATUS_EXPIRED = "expired"
_HIGH_RISK_KEYWORDS = (
    "security",
    "auth",
    "authentication",
    "authorization",
    "permission",
    "integrity",
    "consistency",
    "injection",
    "xss",
    "sql",
)
_REASON_LABEL_MAP: dict[str, str] = {
    "business_exception": "业务特例",
    "historical_debt": "历史债务",
    "rule_false_positive": "规则误报",
    "defer_fix": "暂缓修复",
    "duplicate": "重复问题",
    "other": "其他",
}


@dataclass
class _StrategyAggregate:
    project_id: int
    rule_key: str
    path_pattern: str | None
    signature: str
    sample_count: int = 0
    week_markers: set[str] = field(default_factory=set)
    reason_counter: Counter[str] = field(default_factory=Counter)
    message_samples: list[str] = field(default_factory=list)


def _safe_lower(value: Any) -> str:
    return str(value or "").strip().lower()


def _derive_rule_key(category: str, subcategory: str) -> str:
    category_norm = _safe_lower(category) or "unknown"
    subcategory_norm = _safe_lower(subcategory)
    return f"{category_norm}.{subcategory_norm}" if subcategory_norm else category_norm


def _derive_path_pattern(file_path: str) -> str | None:
    normalized = str(file_path or "").strip().replace("\\", "/")
    if not normalized:
        return None
    parts = [item for item in normalized.split("/") if item]
    if len(parts) <= 1:
        return None
    return f"{parts[0]}/**"


def _is_high_risk(*values: Any) -> bool:
    text = " ".join(str(value or "").strip().lower() for value in values)
    return any(keyword in text for keyword in _HIGH_RISK_KEYWORDS)


def _format_reason_summary(counter: Counter[str]) -> str:
    if not counter:
        return "无明确忽略原因分布。"
    chunks: list[str] = []
    total = max(sum(counter.values()), 1)
    for code, count in counter.most_common(3):
        label = _REASON_LABEL_MAP.get(code, code or "未标注")
        ratio = round(count / total * 100, 1)
        chunks.append(f"{label} {count} 次（{ratio}%）")
    return "；".join(chunks)


def _compute_confidence(*, sample_count: int, active_weeks: int, reason_counter: Counter[str]) -> float:
    sample_score = min(sample_count / 8.0, 1.0)
    week_score = min(active_weeks / 4.0, 1.0)
    if reason_counter:
        consistency = max(reason_counter.values()) / max(sum(reason_counter.values()), 1)
    else:
        consistency = 0.0
    value = 0.55 * sample_score + 0.25 * week_score + 0.2 * consistency
    return round(min(max(value, 0.0), 1.0), 4)


def _resolve_4w_window(anchor_date: date | None, tz_name: str) -> tuple[datetime, datetime]:
    tz = ZoneInfo(tz_name)
    base_day = datetime.now(tz).date() if anchor_date is None else anchor_date
    end_dt_exclusive = datetime.combine(base_day + timedelta(days=1), datetime.min.time())
    start_dt = end_dt_exclusive - timedelta(days=28)
    return start_dt, end_dt_exclusive


def _to_week_marker(value: datetime) -> str:
    marker = value.date() - timedelta(days=value.weekday())
    return marker.isoformat()


async def _mark_expired_strategies(
    db: AsyncSession,
    *,
    now: datetime,
    project_id: int | None,
) -> int:
    stmt = select(ProjectIgnoreStrategy).where(
        ProjectIgnoreStrategy.status == _STATUS_ACTIVE,
        ProjectIgnoreStrategy.expire_at.is_not(None),
        ProjectIgnoreStrategy.expire_at < now,
    )
    if project_id is not None:
        stmt = stmt.where(ProjectIgnoreStrategy.project_id == project_id)
    rows = (await db.execute(stmt)).scalars().all()
    for row in rows:
        row.status = _STATUS_EXPIRED
    return len(rows)


async def _upsert_strategy(
    db: AsyncSession,
    *,
    now: datetime,
    ttl_days: int,
    aggregate: _StrategyAggregate,
    confidence_score: float,
) -> ProjectIgnoreStrategy:
    conditions = [
        ProjectIgnoreStrategy.project_id == aggregate.project_id,
        ProjectIgnoreStrategy.signature == aggregate.signature,
    ]
    if aggregate.path_pattern is None:
        conditions.append(ProjectIgnoreStrategy.path_pattern.is_(None))
    else:
        conditions.append(ProjectIgnoreStrategy.path_pattern == aggregate.path_pattern)
    existing = (
        await db.execute(
            select(ProjectIgnoreStrategy)
            .where(and_(*conditions))
            .order_by(ProjectIgnoreStrategy.id.desc())
            .limit(1)
        )
    ).scalars().first()

    reason_summary = _format_reason_summary(aggregate.reason_counter)
    sample_message = aggregate.message_samples[0] if aggregate.message_samples else "该模式在最近 4 周内重复出现。"
    ignore_condition = (
        f"当规则 `{aggregate.rule_key}`"
        f"{' 且路径命中 ' + aggregate.path_pattern if aggregate.path_pattern else ''}"
        " 时，可降级为忽略级提示。"
    )
    boundary_condition = "若涉及安全/鉴权/数据一致性，请勿忽略并保持强提醒。"
    expire_at = now + timedelta(days=max(1, ttl_days))

    target = existing or ProjectIgnoreStrategy(
        project_id=aggregate.project_id,
        rule_key=aggregate.rule_key,
        path_pattern=aggregate.path_pattern,
        signature=aggregate.signature,
    )
    target.rule_key = aggregate.rule_key
    target.path_pattern = aggregate.path_pattern
    target.signature = aggregate.signature
    target.title = f"{aggregate.rule_key} 高频忽略模式"
    target.reason_summary = reason_summary
    target.ignore_condition = ignore_condition
    target.boundary_condition = boundary_condition
    target.sample_count_4w = aggregate.sample_count
    target.active_weeks_4w = len(aggregate.week_markers)
    target.confidence_score = confidence_score
    target.status = _STATUS_ACTIVE
    target.effective_at = now
    target.expire_at = expire_at
    target.disabled_at = None
    target.disabled_reason = ""

    if existing is None:
        db.add(target)
    return target


async def generate_ignore_strategy_weekly_report(
    db: AsyncSession,
    *,
    project_id: int | None = None,
    anchor_date: date | None = None,
    apply_changes: bool = True,
    sample_threshold: int = 5,
    active_weeks_threshold: int = 2,
    confidence_threshold: float = 0.75,
    ttl_days: int = 14,
) -> dict[str, Any]:
    settings = get_settings()
    start_dt, end_dt_exclusive = _resolve_4w_window(anchor_date, settings.TIMEZONE)
    now = datetime.now(UTC).replace(tzinfo=None)
    normalized_project_id = int(project_id) if project_id is not None else None

    rows_stmt = (
        select(
            MergeRequestReview.project_id,
            ReviewFinding.category,
            ReviewFinding.subcategory,
            ReviewFinding.file_path,
            ReviewFinding.message,
            ReviewFindingAction.action_at,
            ReviewFindingAction.ignore_reason_code,
        )
        .select_from(ReviewFindingAction)
        .join(ReviewFinding, ReviewFinding.id == ReviewFindingAction.finding_id)
        .join(MergeRequestReview, MergeRequestReview.id == ReviewFinding.review_id)
        .where(
            ReviewFindingAction.action_type == _IGNORED_ACTION_TYPE,
            ReviewFindingAction.action_at >= start_dt,
            ReviewFindingAction.action_at < end_dt_exclusive,
            ReviewFindingAction.ignore_reason_code != "",
        )
    )
    if normalized_project_id is not None:
        rows_stmt = rows_stmt.where(MergeRequestReview.project_id == normalized_project_id)
    rows = (await db.execute(rows_stmt)).all()

    aggregates: dict[tuple[int, str, str | None, str], _StrategyAggregate] = {}
    ignored_high_risk_count = 0
    for row in rows:
        pid = int(row.project_id)
        category = str(row.category or "")
        subcategory = str(row.subcategory or "")
        rule_key = _derive_rule_key(category, subcategory)
        if _is_high_risk(category, subcategory, rule_key):
            ignored_high_risk_count += 1
            continue

        path_pattern = _derive_path_pattern(str(row.file_path or ""))
        signature = f"{rule_key}|{path_pattern or '*'}"
        key = (pid, rule_key, path_pattern, signature)
        aggregate = aggregates.get(key)
        if aggregate is None:
            aggregate = _StrategyAggregate(
                project_id=pid,
                rule_key=rule_key,
                path_pattern=path_pattern,
                signature=signature,
            )
            aggregates[key] = aggregate
        aggregate.sample_count += 1
        if isinstance(row.action_at, datetime):
            aggregate.week_markers.add(_to_week_marker(row.action_at))
        reason_code = _safe_lower(row.ignore_reason_code) or "other"
        aggregate.reason_counter[reason_code] += 1
        message = str(row.message or "").strip()
        if message and len(aggregate.message_samples) < 3:
            aggregate.message_samples.append(message)

    expired_count = await _mark_expired_strategies(
        db,
        now=now,
        project_id=normalized_project_id,
    ) if apply_changes else 0

    candidates_by_project: dict[int, list[dict[str, Any]]] = defaultdict(list)
    activated_count = 0
    for aggregate in aggregates.values():
        active_weeks = len(aggregate.week_markers)
        confidence = _compute_confidence(
            sample_count=aggregate.sample_count,
            active_weeks=active_weeks,
            reason_counter=aggregate.reason_counter,
        )
        eligible = (
            aggregate.sample_count >= sample_threshold
            and active_weeks >= active_weeks_threshold
            and confidence >= confidence_threshold
        )
        item = {
            "rule_key": aggregate.rule_key,
            "path_pattern": aggregate.path_pattern,
            "signature": aggregate.signature,
            "sample_count_4w": aggregate.sample_count,
            "active_weeks_4w": active_weeks,
            "confidence_score": confidence,
            "eligible": eligible,
            "reason_summary": _format_reason_summary(aggregate.reason_counter),
        }
        candidates_by_project[aggregate.project_id].append(item)
        if eligible and apply_changes:
            await _upsert_strategy(
                db,
                now=now,
                ttl_days=ttl_days,
                aggregate=aggregate,
                confidence_score=confidence,
            )
            activated_count += 1

    projects = []
    for pid, items in sorted(candidates_by_project.items(), key=lambda pair: pair[0]):
        sorted_items = sorted(
            items,
            key=lambda item: (-int(item["sample_count_4w"]), -float(item["confidence_score"])),
        )
        projects.append(
            {
                "project_id": pid,
                "candidate_count": len(sorted_items),
                "eligible_count": sum(1 for item in sorted_items if bool(item["eligible"])),
                "candidates": sorted_items,
            }
        )

    if apply_changes:
        await db.commit()

    return {
        "window_start": start_dt.date().isoformat(),
        "window_end": (end_dt_exclusive - timedelta(days=1)).date().isoformat(),
        "summary": {
            "raw_ignored_actions": len(rows),
            "high_risk_filtered": ignored_high_risk_count,
            "candidate_count": int(sum(item["candidate_count"] for item in projects)),
            "eligible_count": int(sum(item["eligible_count"] for item in projects)),
            "activated_count": int(activated_count),
            "expired_count": int(expired_count),
            "project_count": len(projects),
            "apply_changes": bool(apply_changes),
        },
        "projects": projects,
        "generated_at": now.isoformat(timespec="seconds"),
    }


async def build_ignore_strategy_prompt_for_project(
    db: AsyncSession,
    *,
    project_id: int,
    now: datetime | None = None,
    limit: int = 8,
) -> str:
    current = now or datetime.now(UTC).replace(tzinfo=None)
    rows = (
        await db.execute(
            select(ProjectIgnoreStrategy)
            .where(
                ProjectIgnoreStrategy.project_id == project_id,
                ProjectIgnoreStrategy.status == _STATUS_ACTIVE,
                or_(
                    ProjectIgnoreStrategy.expire_at.is_(None),
                    ProjectIgnoreStrategy.expire_at >= current,
                ),
            )
            .order_by(
                ProjectIgnoreStrategy.confidence_score.desc(),
                ProjectIgnoreStrategy.sample_count_4w.desc(),
                ProjectIgnoreStrategy.id.desc(),
            )
            .limit(max(1, int(limit))),
        )
    ).scalars().all()
    if not rows:
        return ""

    lines = [
        "【仓库级忽略级策略（自动生成）】",
        "以下策略仅用于降噪，不适用于安全/鉴权/数据一致性问题：",
    ]
    for item in rows:
        scope = f" @ {item.path_pattern}" if item.path_pattern else ""
        lines.append(
            (
                f"- {item.rule_key}{scope}：{item.ignore_condition} "
                f"(样本 {item.sample_count_4w}，稳定周数 {item.active_weeks_4w}，置信度 {item.confidence_score})"
            )
        )
    return "\n".join(lines)
