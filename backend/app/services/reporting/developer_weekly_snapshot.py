from __future__ import annotations

import json
import re
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.llm import llm_router
from app.llm.types import LLMRequest
from app.models import DeveloperWeeklySummary
from app.services.reporting.developer_weekly import (
    _build_week_window,
    _resolve_include_statuses,
    generate_developer_weekly_cards,
    generate_developer_weekly_report,
)


def _build_last_week_window(reference_date: date | None, tz_name: str) -> tuple[date, date]:
    tz = ZoneInfo(tz_name)
    current_date = datetime.now(tz).date() if reference_date is None else reference_date
    current_week_start = current_date - timedelta(days=current_date.weekday())
    week_start = current_week_start - timedelta(days=7)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def _build_statuses_key(include_statuses: list[str]) -> str:
    return ",".join(include_statuses)


def _parse_llm_summary_payload(content: str) -> dict[str, Any] | None:
    text = str(content or "").strip()
    if not text:
        return None
    candidates = [text]
    fenced_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, flags=re.IGNORECASE)
    if fenced_match:
        candidates.append(fenced_match.group(1))
    loose_match = re.search(r"(\{[\s\S]*\})", text)
    if loose_match:
        candidates.append(loose_match.group(1))
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


async def _generate_llm_summary(
    db: AsyncSession,
    *,
    report: dict[str, Any],
) -> tuple[str | None, list[str] | None, str | None, str | None, str | None]:
    try:
        provider = await llm_router.resolve_provider(0, db)
        summary_input = {
            "week_start": report.get("week_start"),
            "week_end": report.get("week_end"),
            "owner": report.get("owner"),
            "summary": report.get("summary"),
            "by_category": report.get("by_category"),
            "by_severity": report.get("by_severity"),
            "top_files": report.get("top_files"),
            "projects": report.get("projects"),
            "gap_checklist": report.get("gap_checklist"),
        }
        prompt = (
            "请基于以下成员周报统计，生成中文总结。\n"
            "必须返回 JSON，格式为：\n"
            '{"summary":"...","gap_checklist":["...","..."]}\n'
            "要求：summary 60-180 字；gap_checklist 2-4 条，每条不超过 40 字。\n\n"
            f"输入数据：\n{json.dumps(summary_input, ensure_ascii=False)}"
        )
        response = await llm_router.review(
            provider,
            LLMRequest(
                system_message="你是研发效能周报助手。输出必须是合法 JSON，不要输出额外文本。",
                prompt=prompt,
                temperature=0.2,
                max_tokens=1200,
            ),
        )
        parsed = _parse_llm_summary_payload(response.content)
        if not parsed:
            return None, None, provider.name, response.model, "invalid_llm_json"
        summary = str(parsed.get("summary") or "").strip()
        if not summary:
            return None, None, provider.name, response.model, "empty_llm_summary"
        gaps_raw = parsed.get("gap_checklist")
        gap_checklist = (
            [str(item).strip() for item in gaps_raw if str(item).strip()]
            if isinstance(gaps_raw, list)
            else []
        )
        return summary, gap_checklist[:4], provider.name, response.model, None
    except Exception as exc:
        return None, None, None, None, str(exc)


async def get_cached_developer_weekly_cards(
    db: AsyncSession,
    *,
    anchor_date: date | None = None,
    limit: int = 30,
    include_statuses: list[str] | None = None,
) -> dict[str, Any] | None:
    settings = get_settings()
    week_start, week_end, _, _ = _build_week_window(anchor_date, settings.TIMEZONE)
    normalized_include_statuses = await _resolve_include_statuses(db, include_statuses=include_statuses)
    statuses_key = _build_statuses_key(normalized_include_statuses)

    rows = (
        await db.execute(
            select(DeveloperWeeklySummary)
            .where(
                DeveloperWeeklySummary.week_start == week_start,
                DeveloperWeeklySummary.include_statuses_key == statuses_key,
                DeveloperWeeklySummary.status == "completed",
            )
            .order_by(DeveloperWeeklySummary.owner_name.asc())
        )
    ).scalars().all()
    if not rows:
        return None

    cards = [dict(row.card_payload or {}) for row in rows if isinstance(row.card_payload, dict)]
    cards.sort(key=lambda item: (-int(item.get("total_findings") or 0), str(item.get("owner") or "")))
    normalized_limit = max(1, min(int(limit or 30), 200))
    results = cards[:normalized_limit]
    latest_generated_at = max(row.generated_at for row in rows)
    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "include_statuses": normalized_include_statuses,
        "count": len(results),
        "results": results,
        "generated_at": latest_generated_at.isoformat(timespec="seconds"),
        "source": "snapshot",
    }


async def get_cached_developer_weekly_report(
    db: AsyncSession,
    *,
    owner: str | None = None,
    owner_email: str | None = None,
    anchor_date: date | None = None,
    include_statuses: list[str] | None = None,
) -> dict[str, Any] | None:
    settings = get_settings()
    week_start, _, _, _ = _build_week_window(anchor_date, settings.TIMEZONE)
    normalized_include_statuses = await _resolve_include_statuses(db, include_statuses=include_statuses)
    statuses_key = _build_statuses_key(normalized_include_statuses)

    stmt = select(DeveloperWeeklySummary).where(
        DeveloperWeeklySummary.week_start == week_start,
        DeveloperWeeklySummary.include_statuses_key == statuses_key,
        DeveloperWeeklySummary.status == "completed",
    )
    normalized_owner = str(owner or "").strip()
    normalized_owner_email = str(owner_email or "").strip()
    if normalized_owner:
        stmt = stmt.where(DeveloperWeeklySummary.owner_name == normalized_owner)
    elif normalized_owner_email:
        stmt = stmt.where(DeveloperWeeklySummary.owner_email == normalized_owner_email)
    else:
        return None

    row = (await db.execute(stmt.limit(1))).scalars().first()
    if row is None or not isinstance(row.report_payload, dict):
        return None

    payload = dict(row.report_payload)
    payload["include_statuses"] = normalized_include_statuses
    payload["generated_at"] = row.generated_at.isoformat(timespec="seconds")
    payload["source"] = row.source
    return payload


async def generate_last_week_developer_weekly_summaries(
    db: AsyncSession,
    *,
    reference_date: date | None = None,
    include_statuses: list[str] | None = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    settings = get_settings()
    week_start, week_end = _build_last_week_window(reference_date, settings.TIMEZONE)
    normalized_include_statuses = await _resolve_include_statuses(db, include_statuses=include_statuses)
    statuses_key = _build_statuses_key(normalized_include_statuses)

    cards = await generate_developer_weekly_cards(
        db,
        anchor_date=week_start,
        limit=500,
        include_statuses=normalized_include_statuses,
    )
    rows = list(cards.get("results") or [])

    await db.execute(
        delete(DeveloperWeeklySummary).where(
            DeveloperWeeklySummary.week_start == week_start,
            DeveloperWeeklySummary.include_statuses_key == statuses_key,
        )
    )

    generated_count = 0
    llm_count = 0
    heuristic_count = 0
    failed_count = 0
    now_utc = datetime.now(UTC).replace(tzinfo=None)

    for card in rows:
        owner = str(card.get("owner") or "").strip()
        if not owner:
            continue
        report = await generate_developer_weekly_report(
            db,
            owner=owner,
            anchor_date=week_start,
            include_statuses=normalized_include_statuses,
        )
        ai_summary = str(report.get("ai_summary") or "").strip()
        gap_checklist = report.get("gap_checklist") if isinstance(report.get("gap_checklist"), list) else []
        source = "heuristic"
        llm_provider: str | None = None
        llm_model: str | None = None
        error_message: str | None = None

        if use_llm and int(report.get("summary", {}).get("total_findings") or 0) > 0:
            llm_summary, llm_gaps, llm_provider, llm_model, llm_error = await _generate_llm_summary(
                db,
                report=report,
            )
            if llm_summary:
                ai_summary = llm_summary
                if llm_gaps:
                    gap_checklist = llm_gaps
                source = "llm"
            elif llm_error:
                error_message = llm_error

        report_payload = dict(report)
        report_payload["ai_summary"] = ai_summary
        report_payload["gap_checklist"] = gap_checklist
        report_payload["source"] = source
        report_payload["generated_at"] = now_utc.isoformat(timespec="seconds")
        report_payload["include_statuses"] = normalized_include_statuses

        card_payload = dict(card)
        card_payload["summary_excerpt"] = ai_summary[:120]
        card_payload["improvement_focus"] = (
            str(gap_checklist[0]) if gap_checklist else str(card_payload.get("improvement_focus") or "建议保持当前自检节奏。")
        )
        card_payload["include_statuses"] = normalized_include_statuses

        db.add(
            DeveloperWeeklySummary(
                week_start=week_start,
                week_end=week_end,
                owner_name=owner,
                owner_email=str(report.get("owner_email") or "").strip() or None,
                include_statuses_key=statuses_key,
                include_statuses=normalized_include_statuses,
                status="completed",
                source=source,
                llm_provider=llm_provider,
                llm_model=llm_model,
                error_message=error_message,
                ai_summary=ai_summary,
                report_payload=report_payload,
                card_payload=card_payload,
                generated_at=now_utc,
            )
        )
        generated_count += 1
        if source == "llm":
            llm_count += 1
        else:
            heuristic_count += 1
        if error_message:
            failed_count += 1

    await db.flush()
    return {
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
        "include_statuses": normalized_include_statuses,
        "candidate_count": len(rows),
        "generated_count": generated_count,
        "llm_count": llm_count,
        "heuristic_count": heuristic_count,
        "failed_count": failed_count,
        "generated_at": now_utc.isoformat(timespec="seconds"),
    }
