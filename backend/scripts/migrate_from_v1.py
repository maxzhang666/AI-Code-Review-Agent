from __future__ import annotations

import argparse
import ast
import asyncio
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app.models  # noqa: F401
import app.database as db_module
from app.config import get_settings
from app.database import get_session_factory, init_db
from app.models import (
    GitLabConfig,
    LLMProvider,
    MergeRequestReview,
    NotificationChannel,
    Project,
    ProjectNotificationSetting,
    ProjectWebhookEventPrompt,
    WebhookEventRule,
    WebhookLog,
)


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table_name,),
    ).fetchone()
    return row is not None


def _fetch_rows(conn: sqlite3.Connection, table_name: str) -> list[sqlite3.Row]:
    if not _table_exists(conn, table_name):
        return []
    cursor = conn.execute(f"SELECT * FROM {table_name}")
    return list(cursor.fetchall())


def _row_get(row: sqlite3.Row, key: str, default: Any = None) -> Any:
    return row[key] if key in row.keys() else default


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        raw = value.strip().lower()
        if raw in {"1", "true", "yes", "on"}:
            return True
        if raw in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def _to_int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if raw.isdigit():
            return int(raw)
    return default


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        normalized = raw.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
            return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
        except ValueError:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(raw, fmt)
            except ValueError:
                continue
    return None


def _dt_or_now(value: Any) -> datetime:
    parsed = _parse_datetime(value)
    return parsed or datetime.now()


def _parse_json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        try:
            return ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            return default
    return default


def _parse_dict(value: Any) -> dict[str, Any]:
    parsed = _parse_json(value, default={})
    return parsed if isinstance(parsed, dict) else {}


def _parse_list(value: Any) -> list[Any]:
    parsed = _parse_json(value, default=[])
    return parsed if isinstance(parsed, list) else []


def _parse_json_or_raw(value: Any, default: Any) -> Any:
    if value is None:
        return default
    parsed = _parse_json(value, default=None)
    if parsed is not None:
        return parsed
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


async def _truncate_target(session: AsyncSession) -> None:
    # Delete child tables first to satisfy FK constraints.
    await session.execute(delete(ProjectNotificationSetting))
    await session.execute(delete(ProjectWebhookEventPrompt))
    await session.execute(delete(MergeRequestReview))
    await session.execute(delete(WebhookLog))
    await session.execute(delete(Project))
    await session.execute(delete(NotificationChannel))
    await session.execute(delete(WebhookEventRule))
    await session.execute(delete(GitLabConfig))
    await session.execute(delete(LLMProvider))


async def _migrate_llm_providers(conn: sqlite3.Connection, session: AsyncSession) -> int:
    count = 0
    used_ids: set[int] = set()
    next_id = 1

    for row in _fetch_rows(conn, "llm_configs"):
        provider_id = _to_int(_row_get(row, "id"), next_id) or next_id
        while provider_id in used_ids:
            provider_id += 1
        used_ids.add(provider_id)
        next_id = max(next_id, provider_id + 1)

        provider_name = str(_row_get(row, "provider", "openai") or "openai")
        model_name = str(_row_get(row, "model", "") or "")
        name = f"{provider_name}-{model_name}" if model_name else provider_name
        config_data = {
            "provider_name": provider_name,
            "api_key": str(_row_get(row, "api_key", "") or ""),
            "api_base": str(_row_get(row, "api_base", "") or ""),
            "model": model_name,
        }
        session.add(
            LLMProvider(
                id=provider_id,
                name=name,
                protocol="openai_compatible",
                is_active=_to_bool(_row_get(row, "is_active"), True),
                config_data=config_data,
                created_at=_dt_or_now(_row_get(row, "created_at")),
                updated_at=_dt_or_now(_row_get(row, "updated_at")),
            )
        )
        count += 1

    for row in _fetch_rows(conn, "claude_cli_configs"):
        provider_id = _to_int(_row_get(row, "id"), next_id) or next_id
        while provider_id in used_ids:
            provider_id += 1
        used_ids.add(provider_id)
        next_id = max(next_id, provider_id + 1)

        config_data = {
            "cli_path": str(_row_get(row, "cli_path", "claude") or "claude"),
            "timeout": _to_int(_row_get(row, "timeout"), 300) or 300,
            "anthropic_base_url": str(_row_get(row, "anthropic_base_url", "") or ""),
            "anthropic_auth_token": str(_row_get(row, "anthropic_auth_token", "") or ""),
        }
        session.add(
            LLMProvider(
                id=provider_id,
                name=f"claude-cli-{provider_id}",
                protocol="claude_cli",
                is_active=_to_bool(_row_get(row, "is_active"), True),
                config_data=config_data,
                created_at=_dt_or_now(_row_get(row, "created_at")),
                updated_at=_dt_or_now(_row_get(row, "updated_at")),
            )
        )
        count += 1

    return count


async def _migrate_projects(conn: sqlite3.Connection, session: AsyncSession) -> int:
    count = 0
    for row in _fetch_rows(conn, "projects"):
        session.add(
            Project(
                id=_to_int(_row_get(row, "id"), 0) or 0,
                project_id=_to_int(_row_get(row, "project_id"), 0) or 0,
                project_name=str(_row_get(row, "project_name", "") or "")[:255],
                project_path=str(_row_get(row, "project_path", "") or "")[:500],
                project_url=str(_row_get(row, "project_url", "") or "")[:500],
                namespace=str(_row_get(row, "namespace", "") or "")[:255],
                review_enabled=_to_bool(_row_get(row, "review_enabled"), False),
                auto_review_on_mr=_to_bool(_row_get(row, "auto_review_on_mr"), True),
                gitlab_comment_notifications_enabled=_to_bool(
                    _row_get(row, "gitlab_comment_notifications_enabled"), True
                ),
                enabled_webhook_events=_parse_list(_row_get(row, "enabled_webhook_events")),
                exclude_file_types=_parse_list(_row_get(row, "exclude_file_types")),
                ignore_file_patterns=_parse_list(_row_get(row, "ignore_file_patterns")),
                gitlab_data=_parse_dict(_row_get(row, "gitlab_data")),
                created_at=_dt_or_now(_row_get(row, "created_at")),
                updated_at=_dt_or_now(_row_get(row, "updated_at")),
                last_webhook_at=_parse_datetime(_row_get(row, "last_webhook_at")),
                default_llm_provider_id=_to_int(_row_get(row, "default_llm_provider_id"), None),
            )
        )
        count += 1
    return count


async def _migrate_webhook_logs(conn: sqlite3.Connection, session: AsyncSession) -> int:
    count = 0
    for row in _fetch_rows(conn, "webhook_logs"):
        session.add(
            WebhookLog(
                id=_to_int(_row_get(row, "id"), 0) or 0,
                event_type=str(_row_get(row, "event_type", "") or "")[:100],
                project_id=_to_int(_row_get(row, "project_id"), 0) or 0,
                project_name=str(_row_get(row, "project_name", "") or "")[:255],
                merge_request_iid=_to_int(_row_get(row, "merge_request_iid"), None),
                user_name=str(_row_get(row, "user_name", "") or "")[:255],
                user_email=str(_row_get(row, "user_email", "") or "")[:255],
                source_branch=str(_row_get(row, "source_branch", "") or "")[:255],
                target_branch=str(_row_get(row, "target_branch", "") or "")[:255],
                payload=_parse_dict(_row_get(row, "payload")),
                request_headers=_parse_dict(_row_get(row, "request_headers")),
                request_body_raw=str(_row_get(row, "request_body_raw", "") or ""),
                remote_addr=(
                    str(_row_get(row, "remote_addr")).strip()
                    if _row_get(row, "remote_addr") not in (None, "")
                    else None
                ),
                user_agent=(
                    str(_row_get(row, "user_agent")).strip()
                    if _row_get(row, "user_agent") not in (None, "")
                    else None
                ),
                request_id=(
                    str(_row_get(row, "request_id")).strip()
                    if _row_get(row, "request_id") not in (None, "")
                    else None
                ),
                created_at=_dt_or_now(_row_get(row, "created_at")),
                processed=_to_bool(_row_get(row, "processed"), False),
                processed_at=_parse_datetime(_row_get(row, "processed_at")),
                log_level=str(_row_get(row, "log_level", "INFO") or "INFO"),
                skip_reason=(
                    str(_row_get(row, "skip_reason")).strip()
                    if _row_get(row, "skip_reason") not in (None, "")
                    else None
                ),
                error_message=(
                    str(_row_get(row, "error_message")).strip()
                    if _row_get(row, "error_message") not in (None, "")
                    else None
                ),
            )
        )
        count += 1
    return count


async def _migrate_reviews(conn: sqlite3.Connection, session: AsyncSession) -> int:
    count = 0
    for row in _fetch_rows(conn, "merge_request_reviews"):
        session.add(
            MergeRequestReview(
                id=_to_int(_row_get(row, "id"), 0) or 0,
                project_id=_to_int(_row_get(row, "project_id"), 0) or 0,
                project_name=str(_row_get(row, "project_name", "") or "")[:255],
                merge_request_iid=_to_int(_row_get(row, "merge_request_iid"), 0) or 0,
                merge_request_title=str(_row_get(row, "merge_request_title", "") or "")[:500],
                source_branch=str(_row_get(row, "source_branch", "") or "")[:255],
                target_branch=str(_row_get(row, "target_branch", "") or "")[:255],
                author_name=str(_row_get(row, "author_name", "") or "")[:255],
                author_email=str(_row_get(row, "author_email", "") or "")[:255],
                review_content=str(_row_get(row, "review_content", "") or ""),
                review_score=_to_int(_row_get(row, "review_score"), None),
                files_reviewed=_parse_list(_row_get(row, "files_reviewed")),
                total_files=_to_int(_row_get(row, "total_files"), 0) or 0,
                status=str(_row_get(row, "status", "pending") or "pending"),
                created_at=_dt_or_now(_row_get(row, "created_at")),
                updated_at=_dt_or_now(_row_get(row, "updated_at")),
                completed_at=_parse_datetime(_row_get(row, "completed_at")),
                error_message=(
                    str(_row_get(row, "error_message")).strip()
                    if _row_get(row, "error_message") not in (None, "")
                    else None
                ),
                response_sent=_to_bool(_row_get(row, "response_sent"), False),
                response_type=(
                    str(_row_get(row, "response_type")).strip()
                    if _row_get(row, "response_type") not in (None, "")
                    else None
                ),
                llm_provider=(
                    str(_row_get(row, "llm_provider")).strip()
                    if _row_get(row, "llm_provider") not in (None, "")
                    else None
                ),
                llm_model=(
                    str(_row_get(row, "llm_model")).strip()
                    if _row_get(row, "llm_model") not in (None, "")
                    else None
                ),
                is_mock=_to_bool(_row_get(row, "is_mock"), False),
                notification_sent=_to_bool(_row_get(row, "notification_sent"), False),
                notification_result=_parse_dict(_row_get(row, "notification_result")),
                request_id=(
                    str(_row_get(row, "request_id")).strip()
                    if _row_get(row, "request_id") not in (None, "")
                    else None
                ),
            )
        )
        count += 1
    return count


async def _migrate_gitlab_configs(conn: sqlite3.Connection, session: AsyncSession) -> int:
    count = 0
    for row in _fetch_rows(conn, "gitlab_configs"):
        session.add(
            GitLabConfig(
                id=_to_int(_row_get(row, "id"), 0) or 0,
                server_url=str(_row_get(row, "server_url", "https://gitlab.com") or "https://gitlab.com")[:500],
                private_token=str(_row_get(row, "private_token", "") or "")[:500],
                is_active=_to_bool(_row_get(row, "is_active"), True),
                created_at=_dt_or_now(_row_get(row, "created_at")),
                updated_at=_dt_or_now(_row_get(row, "updated_at")),
            )
        )
        count += 1
    return count


async def _migrate_notification_channels(conn: sqlite3.Connection, session: AsyncSession) -> int:
    count = 0
    for row in _fetch_rows(conn, "notification_channels"):
        session.add(
            NotificationChannel(
                id=_to_int(_row_get(row, "id"), 0) or 0,
                name=str(_row_get(row, "name", "") or "")[:255],
                notification_type=str(_row_get(row, "notification_type", "") or "")[:50],
                description=str(_row_get(row, "description", "") or ""),
                is_active=_to_bool(_row_get(row, "is_active"), True),
                is_default=_to_bool(_row_get(row, "is_default"), False),
                config_data=_parse_dict(_row_get(row, "config_data")),
                created_at=_dt_or_now(_row_get(row, "created_at")),
                updated_at=_dt_or_now(_row_get(row, "updated_at")),
            )
        )
        count += 1
    return count


async def _migrate_event_rules(conn: sqlite3.Connection, session: AsyncSession) -> int:
    count = 0
    for row in _fetch_rows(conn, "webhook_event_rules"):
        session.add(
            WebhookEventRule(
                id=_to_int(_row_get(row, "id"), 0) or 0,
                name=str(_row_get(row, "name", "") or "")[:255],
                event_type=str(_row_get(row, "event_type", "") or "")[:100],
                description=str(_row_get(row, "description", "") or ""),
                match_rules=_parse_json_or_raw(_row_get(row, "match_rules"), default={}),
                is_active=_to_bool(_row_get(row, "is_active"), True),
                created_at=_dt_or_now(_row_get(row, "created_at")),
                updated_at=_dt_or_now(_row_get(row, "updated_at")),
            )
        )
        count += 1
    return count


async def _migrate_project_notification_settings(conn: sqlite3.Connection, session: AsyncSession) -> int:
    count = 0
    for row in _fetch_rows(conn, "project_notification_settings"):
        session.add(
            ProjectNotificationSetting(
                id=_to_int(_row_get(row, "id"), 0) or 0,
                project_id=_to_int(_row_get(row, "project_id"), 0) or 0,
                channel_id=_to_int(_row_get(row, "channel_id"), 0) or 0,
                enabled=_to_bool(_row_get(row, "enabled"), True),
                created_at=_dt_or_now(_row_get(row, "created_at")),
                updated_at=_dt_or_now(_row_get(row, "updated_at")),
            )
        )
        count += 1
    return count


async def _migrate_project_prompts(conn: sqlite3.Connection, session: AsyncSession) -> int:
    count = 0
    for row in _fetch_rows(conn, "project_webhook_event_prompts"):
        session.add(
            ProjectWebhookEventPrompt(
                id=_to_int(_row_get(row, "id"), 0) or 0,
                project_id=_to_int(_row_get(row, "project_id"), 0) or 0,
                event_rule_id=_to_int(_row_get(row, "event_rule_id"), 0) or 0,
                custom_prompt=str(_row_get(row, "custom_prompt", "") or ""),
                use_custom=_to_bool(_row_get(row, "use_custom"), False),
                created_at=_dt_or_now(_row_get(row, "created_at")),
                updated_at=_dt_or_now(_row_get(row, "updated_at")),
            )
        )
        count += 1
    return count


async def migrate(source_db: Path, target_db: Path) -> int:
    if not source_db.exists():
        print(f"[ERROR] Source database not found: {source_db}")
        return 1

    target_db.parent.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{target_db}"
    get_settings.cache_clear()

    if db_module._engine is not None:
        await db_module._engine.dispose()
    db_module._engine = None
    db_module._session_factory = None

    await init_db()
    session_factory = get_session_factory()
    summary: dict[str, int] = {}

    with sqlite3.connect(source_db) as conn:
        conn.row_factory = sqlite3.Row
        async with session_factory() as session:
            try:
                await _truncate_target(session)
                summary["llm_providers"] = await _migrate_llm_providers(conn, session)
                summary["projects"] = await _migrate_projects(conn, session)
                summary["webhook_logs"] = await _migrate_webhook_logs(conn, session)
                summary["merge_request_reviews"] = await _migrate_reviews(conn, session)
                summary["gitlab_configs"] = await _migrate_gitlab_configs(conn, session)
                summary["notification_channels"] = await _migrate_notification_channels(conn, session)
                summary["webhook_event_rules"] = await _migrate_event_rules(conn, session)
                summary["project_notification_settings"] = await _migrate_project_notification_settings(conn, session)
                summary["project_webhook_event_prompts"] = await _migrate_project_prompts(conn, session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    if db_module._engine is not None:
        await db_module._engine.dispose()
    db_module._engine = None
    db_module._session_factory = None

    print("Migration finished successfully.")
    for key, value in summary.items():
        print(f"- {key}: {value}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate data from backend/db.sqlite3 to backend-v2/db.sqlite3")
    parser.add_argument(
        "--source",
        type=Path,
        default=REPO_ROOT / "backend" / "db.sqlite3",
        help="Path to source v1 SQLite database.",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=PROJECT_ROOT / "db.sqlite3",
        help="Path to target v2 SQLite database.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    code = asyncio.run(migrate(args.source.resolve(), args.target.resolve()))
    raise SystemExit(code)
