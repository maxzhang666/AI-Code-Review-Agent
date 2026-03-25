from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import MRFeedbackRecord, MergeRequestReview, Project, ReviewFinding

_DEFAULT_REASON_BUCKETS = ["历史包袱", "业务特例", "误报", "已规划后续修复", "其他"]


@dataclass(frozen=True)
class WeekWindow:
    week_start: date
    week_end: date
    start_dt: datetime
    end_dt_exclusive: datetime


def _build_week_window(anchor_date: date | None, tz_name: str) -> WeekWindow:
    tz = ZoneInfo(tz_name)
    today = datetime.now(tz).date() if anchor_date is None else anchor_date
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    start_dt = datetime.combine(week_start, datetime.min.time())
    end_dt_exclusive = datetime.combine(week_end + timedelta(days=1), datetime.min.time())
    return WeekWindow(
        week_start=week_start,
        week_end=week_end,
        start_dt=start_dt,
        end_dt_exclusive=end_dt_exclusive,
    )


def _normalize_rule_key(raw_value: str | None) -> str:
    value = str(raw_value or "").strip()
    return value if value else "未标注规则"


def _bucket_reason(reason: str) -> str:
    normalized = str(reason or "").strip().lower()
    if not normalized:
        return "其他"

    if any(k in normalized for k in ("历史", "legacy", "包袱", "老代码", "技术债", "存量")):
        return "历史包袱"
    if any(k in normalized for k in ("业务特例", "特例", "场景特殊", "业务要求", "客户要求", "例外")):
        return "业务特例"
    if any(k in normalized for k in ("误报", "false positive", "false-positive", "噪音", "不准确", "无效告警")):
        return "误报"
    if any(k in normalized for k in ("后续", "计划", "排期", "重构", "下个迭代", "todo", "待修复")):
        return "已规划后续修复"
    return "其他"


def _build_reason_distribution(counter: Counter[str], denominator: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for key in _DEFAULT_REASON_BUCKETS:
        count = int(counter.get(key, 0))
        ratio = round(count / denominator, 4) if denominator > 0 else 0.0
        results.append({"reason_type": key, "count": count, "ratio": ratio})
    return results


def _build_top_rules(counter: Counter[str], limit: int = 5) -> list[dict[str, Any]]:
    return [
        {"rule_key": rule_key, "ignore_count": int(count)}
        for rule_key, count in counter.most_common(limit)
    ]


def _build_policy_suggestions(
    *,
    ignored_count: int,
    reopened_count: int,
    top_rules: list[dict[str, Any]],
    reason_counter: Counter[str],
) -> list[str]:
    total_actions = ignored_count + reopened_count
    if total_actions <= 0:
        return ["本周暂无回收动作，建议保持现有提醒策略并继续观察。"]

    ignore_rate = ignored_count / total_actions
    false_positive_count = int(reason_counter.get("误报", 0))
    history_count = int(reason_counter.get("历史包袱", 0))
    planned_count = int(reason_counter.get("已规划后续修复", 0))
    lead_rule = str(top_rules[0]["rule_key"]) if top_rules else "未标注规则"

    suggestions: list[str] = []
    if false_positive_count >= max(2, round(ignored_count * 0.3)):
        suggestions.append(f"建议对 `{lead_rule}` 做降噪或阈值调整，减少误报导致的忽略。")
    if history_count >= max(2, round(ignored_count * 0.3)):
        suggestions.append("建议优化提醒文案，明确“历史包袱”场景的处置建议与后续跟踪方式。")
    if planned_count >= max(2, round(ignored_count * 0.25)):
        suggestions.append("建议为“已规划后续修复”补充截止周期提示，避免长期挂起。")
    if reopened_count >= max(1, round(total_actions * 0.25)):
        suggestions.append("回收后重新打开比例偏高，建议保留当前强提醒并追踪规则有效性。")
    if ignore_rate >= 0.8 and ignored_count >= 3:
        suggestions.append("忽略率偏高，建议将高频可忽略问题调整为弱提醒。")

    if not suggestions:
        suggestions.append("本周回收结构稳定，建议保持当前策略并持续观察。")
    return suggestions


async def generate_mr_feedback_weekly_report(
    db: AsyncSession,
    *,
    project_id: int | None = None,
    anchor_date: date | None = None,
) -> dict[str, Any]:
    settings = get_settings()
    window = _build_week_window(anchor_date=anchor_date, tz_name=settings.TIMEZONE)

    feedback_stmt = select(MRFeedbackRecord).where(
        MRFeedbackRecord.created_at >= window.start_dt,
        MRFeedbackRecord.created_at < window.end_dt_exclusive,
    )
    if project_id is not None:
        feedback_stmt = feedback_stmt.where(MRFeedbackRecord.project_id == project_id)
    feedback_rows = (await db.execute(feedback_stmt)).scalars().all()

    issue_stmt = (
        select(MergeRequestReview.project_id, func.count(ReviewFinding.id))
        .select_from(MergeRequestReview)
        .join(ReviewFinding, ReviewFinding.review_id == MergeRequestReview.id)
        .where(
            ReviewFinding.created_at >= window.start_dt,
            ReviewFinding.created_at < window.end_dt_exclusive,
        )
        .group_by(MergeRequestReview.project_id)
    )
    if project_id is not None:
        issue_stmt = issue_stmt.where(MergeRequestReview.project_id == project_id)
    issue_rows = (await db.execute(issue_stmt)).all()
    issue_count_by_project = {int(pid): int(cnt or 0) for pid, cnt in issue_rows}

    project_ids = set(issue_count_by_project.keys())
    for row in feedback_rows:
        project_ids.add(int(row.project_id))
    if project_id is not None:
        project_ids.add(int(project_id))

    project_name_by_id: dict[int, str] = {}
    if project_ids:
        project_rows = (
            await db.execute(
                select(Project.project_id, Project.project_name).where(Project.project_id.in_(project_ids))
            )
        ).all()
        project_name_by_id = {int(pid): str(name or f"项目 {pid}") for pid, name in project_rows}

    feedback_rows_by_project: dict[int, list[MRFeedbackRecord]] = defaultdict(list)
    for row in feedback_rows:
        feedback_rows_by_project[int(row.project_id)].append(row)

    project_summaries: list[dict[str, Any]] = []
    for pid in sorted(project_ids):
        rows = feedback_rows_by_project.get(pid, [])
        ignored_rows = [row for row in rows if row.action == "ignore"]
        reopened_rows = [row for row in rows if row.action == "reopen"]

        ignored_count = len(ignored_rows)
        reopened_count = len(reopened_rows)
        total_feedback_actions = ignored_count + reopened_count
        ignore_rate = round(ignored_count / total_feedback_actions, 4) if total_feedback_actions > 0 else 0.0

        rule_counter = Counter(_normalize_rule_key(row.rule_key) for row in ignored_rows)
        reason_counter = Counter(_bucket_reason(row.reason) for row in ignored_rows)
        top_rules = _build_top_rules(rule_counter)

        project_summaries.append(
            {
                "project_id": pid,
                "project_name": project_name_by_id.get(pid, f"项目 {pid}"),
                "total_issues": int(issue_count_by_project.get(pid, 0)),
                "ignored_count": ignored_count,
                "reopened_count": reopened_count,
                "ignore_rate": ignore_rate,
                "top_ignored_rules": top_rules,
                "ignore_reason_distribution": _build_reason_distribution(reason_counter, ignored_count),
                "suggested_policy_changes": _build_policy_suggestions(
                    ignored_count=ignored_count,
                    reopened_count=reopened_count,
                    top_rules=top_rules,
                    reason_counter=reason_counter,
                ),
            }
        )

    total_issues = int(sum(issue_count_by_project.values()))
    ignored_count_total = sum(int(item["ignored_count"]) for item in project_summaries)
    reopened_count_total = sum(int(item["reopened_count"]) for item in project_summaries)
    total_feedback_actions = ignored_count_total + reopened_count_total
    ignore_rate_total = (
        round(ignored_count_total / total_feedback_actions, 4) if total_feedback_actions > 0 else 0.0
    )

    team_rule_counter = Counter()
    team_reason_counter = Counter()
    for item in project_summaries:
        for rule in item["top_ignored_rules"]:
            team_rule_counter[str(rule["rule_key"])] += int(rule["ignore_count"])
        for bucket in item["ignore_reason_distribution"]:
            team_reason_counter[str(bucket["reason_type"])] += int(bucket["count"])

    team_top_rules = _build_top_rules(team_rule_counter)
    team_reason_distribution = _build_reason_distribution(team_reason_counter, ignored_count_total)
    team_suggestions = _build_policy_suggestions(
        ignored_count=ignored_count_total,
        reopened_count=reopened_count_total,
        top_rules=team_top_rules,
        reason_counter=team_reason_counter,
    )

    return {
        "week_start": window.week_start.isoformat(),
        "week_end": window.week_end.isoformat(),
        "summary": {
            "total_issues": total_issues,
            "ignored_count": ignored_count_total,
            "reopened_count": reopened_count_total,
            "ignore_rate": ignore_rate_total,
            "feedback_actions": total_feedback_actions,
        },
        "top_ignored_rules": team_top_rules,
        "ignore_reason_distribution": team_reason_distribution,
        "suggested_policy_changes": team_suggestions,
        "projects": project_summaries,
        "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(timespec="seconds"),
    }

