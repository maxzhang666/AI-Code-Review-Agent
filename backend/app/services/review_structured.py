from __future__ import annotations

import hashlib
import re
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MergeRequestReview, ReviewFinding

_ALLOWED_SEVERITIES = {"critical", "high", "medium", "low"}


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _to_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _to_confidence(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return 0.0
    if parsed > 1:
        return 1.0
    return parsed


def build_fingerprint(
    *,
    category: str,
    subcategory: str,
    file_path: str,
    line_start: int | None,
    message: str,
) -> str:
    source = "|".join(
        [
            _normalize_text(category),
            _normalize_text(subcategory),
            _normalize_text(file_path),
            str(line_start or 0),
            _normalize_text(message),
        ]
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def normalize_issue(
    issue: Any,
    *,
    default_owner_name: str | None = None,
    default_owner_email: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(issue, dict):
        return None

    severity = _normalize_text(issue.get("severity") or "medium")
    if severity not in _ALLOWED_SEVERITIES:
        severity = "medium"

    category = str(issue.get("category") or "quality").strip() or "quality"
    subcategory = str(issue.get("subcategory") or "").strip()
    file_path = str(issue.get("file_path") or issue.get("file") or "").strip()
    line_start = _to_int(issue.get("line_start"))
    if line_start is None:
        line_start = _to_int(issue.get("line"))
    line_end = _to_int(issue.get("line_end"))
    if line_end is None:
        line_end = line_start

    message = str(issue.get("message") or issue.get("description") or "").strip()
    suggestion = str(issue.get("suggestion") or "").strip()

    owner_name_raw = issue.get("owner_name")
    owner_email_raw = issue.get("owner_email")
    owner_raw = issue.get("owner")

    owner_name = str(owner_name_raw).strip() if owner_name_raw is not None else ""
    owner_email = str(owner_email_raw).strip() if owner_email_raw is not None else ""

    if not owner_name and not owner_email and owner_raw is not None:
        owner_text = str(owner_raw).strip()
        if "@" in owner_text:
            owner_email = owner_text
        else:
            owner_name = owner_text

    if not owner_name and isinstance(default_owner_name, str) and default_owner_name.strip():
        owner_name = default_owner_name.strip()
    if not owner_email and isinstance(default_owner_email, str) and default_owner_email.strip():
        owner_email = default_owner_email.strip()

    owner_display = owner_name or owner_email or None

    confidence = _to_confidence(issue.get("confidence"))
    is_blocking = (
        bool(issue.get("is_blocking"))
        if "is_blocking" in issue
        else severity in {"critical"}
    )
    is_false_positive = bool(issue.get("is_false_positive"))

    fingerprint = build_fingerprint(
        category=category,
        subcategory=subcategory,
        file_path=file_path,
        line_start=line_start,
        message=message,
    )

    return {
        "fingerprint": fingerprint,
        "category": category,
        "subcategory": subcategory,
        "severity": severity,
        "confidence": confidence,
        "file_path": file_path,
        "line_start": line_start,
        "line_end": line_end,
        "message": message,
        "suggestion": suggestion,
        "owner_name": owner_name or None,
        "owner_email": owner_email or None,
        "owner": owner_display,
        "is_blocking": is_blocking,
        "is_false_positive": is_false_positive,
        # Backward-compatible keys for report rendering.
        "file": file_path,
        "line": line_start,
        "description": message,
    }


def normalize_issues(
    issues: Any,
    *,
    default_owner_name: str | None = None,
    default_owner_email: str | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(issues, list):
        return []

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in issues:
        parsed = normalize_issue(
            item,
            default_owner_name=default_owner_name,
            default_owner_email=default_owner_email,
        )
        if parsed is None:
            continue
        fingerprint = str(parsed.get("fingerprint") or "")
        if fingerprint and fingerprint in seen:
            continue
        if fingerprint:
            seen.add(fingerprint)
        normalized.append(parsed)
    return normalized


async def replace_review_findings(
    db: AsyncSession,
    *,
    review: MergeRequestReview,
    issues: Any,
) -> list[ReviewFinding]:
    normalized = normalize_issues(
        issues,
        default_owner_name=(review.author_name or None),
        default_owner_email=(review.author_email or None),
    )

    await db.execute(delete(ReviewFinding).where(ReviewFinding.review_id == review.id))

    rows: list[ReviewFinding] = []
    for item in normalized:
        row = ReviewFinding(
            review_id=review.id,
            fingerprint=str(item.get("fingerprint") or ""),
            category=str(item.get("category") or "quality"),
            subcategory=str(item.get("subcategory") or ""),
            severity=str(item.get("severity") or "medium"),
            confidence=item.get("confidence") if isinstance(item.get("confidence"), (int, float)) else None,
            file_path=str(item.get("file_path") or ""),
            line_start=item.get("line_start") if isinstance(item.get("line_start"), int) else None,
            line_end=item.get("line_end") if isinstance(item.get("line_end"), int) else None,
            message=str(item.get("message") or ""),
            suggestion=str(item.get("suggestion") or ""),
            owner_name=str(item.get("owner_name")) if item.get("owner_name") else None,
            owner_email=str(item.get("owner_email")) if item.get("owner_email") else None,
            owner=str(item.get("owner")) if item.get("owner") else None,
            is_blocking=bool(item.get("is_blocking")),
            is_false_positive=bool(item.get("is_false_positive")),
        )
        rows.append(row)

    if rows:
        db.add_all(rows)
        await db.flush()
    return rows


async def get_review_findings(db: AsyncSession, *, review_id: int) -> list[ReviewFinding]:
    return (
        await db.execute(
            select(ReviewFinding)
            .where(ReviewFinding.review_id == review_id)
            .order_by(ReviewFinding.created_at.desc(), ReviewFinding.id.desc())
        )
    ).scalars().all()


async def materialize_review_findings_from_legacy(
    db: AsyncSession,
    *,
    review: MergeRequestReview,
) -> list[ReviewFinding]:
    existing = await get_review_findings(db, review_id=review.id)
    if existing:
        return existing

    if isinstance(review.review_issues, list) and review.review_issues:
        await replace_review_findings(db, review=review, issues=review.review_issues)
        await db.commit()
        return await get_review_findings(db, review_id=review.id)

    return []
