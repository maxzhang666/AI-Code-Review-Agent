from __future__ import annotations

import argparse
import ast
import asyncio
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine
from sqlalchemy.sql.sqltypes import JSON, Boolean, DateTime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app.models  # noqa: F401
from app.database import Base, _migrate_columns


def _quote_sqlite_identifier(name: str) -> str:
    # Avoid backslashes in f-string expressions for Python 3.11 compatibility.
    return '"' + name.replace('"', '""') + '"'


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
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


def _parse_json_like(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list, bool, int, float)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return value
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        try:
            return ast.literal_eval(raw)
        except (ValueError, SyntaxError):
            return value
    return value


def _to_bool(value: Any) -> bool:
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


def _normalize_value(column: sa.Column[Any], value: Any) -> Any:
    if value is None:
        return None
    if isinstance(column.type, JSON):
        return _parse_json_like(value)
    if isinstance(column.type, DateTime):
        parsed = _parse_datetime(value)
        return parsed if parsed is not None else value
    if isinstance(column.type, Boolean):
        return _to_bool(value)
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8", errors="replace")
    return value


def _list_source_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    return {str(row[0]) for row in rows}


def _list_source_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    escaped_name = table_name.replace('"', '""')
    rows = conn.execute(f'PRAGMA table_info("{escaped_name}")').fetchall()
    return {str(row[1]) for row in rows}


def _iter_source_rows(
    conn: sqlite3.Connection,
    table_name: str,
    columns: list[str],
    batch_size: int,
):
    if not columns:
        return
    select_columns = ", ".join(_quote_sqlite_identifier(column) for column in columns)
    sql = f"SELECT {select_columns} FROM {_quote_sqlite_identifier(table_name)}"
    cursor = conn.execute(sql)
    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break
        yield rows


async def _create_target_schema(target_conn: AsyncConnection) -> None:
    await target_conn.run_sync(Base.metadata.create_all)
    await target_conn.run_sync(_migrate_columns)


async def _truncate_target_tables(target_conn: AsyncConnection) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        await target_conn.execute(sa.delete(table))


async def _sync_postgres_sequences(target_conn: AsyncConnection) -> None:
    if target_conn.dialect.name != "postgresql":
        return

    for table in Base.metadata.sorted_tables:
        integer_pk_columns = [
            column
            for column in table.primary_key.columns
            if isinstance(column.type, sa.Integer)
        ]
        if not integer_pk_columns:
            continue

        qualified_name = table.name if table.schema is None else f"{table.schema}.{table.name}"
        for column in integer_pk_columns:
            sequence = (
                await target_conn.execute(
                    sa.text(
                        "SELECT pg_get_serial_sequence(:table_name, :column_name)"
                    ),
                    {
                        "table_name": qualified_name,
                        "column_name": column.name,
                    },
                )
            ).scalar_one_or_none()
            if not sequence:
                continue

            max_value = (await target_conn.execute(sa.select(sa.func.max(column)))).scalar_one_or_none()
            next_value = int(max_value) + 1 if max_value is not None else 1
            await target_conn.execute(
                sa.text("SELECT setval(CAST(:sequence AS regclass), :next_value, false)"),
                {"sequence": sequence, "next_value": next_value},
            )


async def migrate_sqlite_to_database(
    source_sqlite: Path,
    target_url: str,
    *,
    truncate: bool = False,
    batch_size: int = 500,
    allow_non_postgres: bool = False,
) -> dict[str, int]:
    if not source_sqlite.exists():
        raise FileNotFoundError(f"Source SQLite database not found: {source_sqlite}")
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")
    if not allow_non_postgres and not target_url.startswith("postgresql"):
        raise ValueError("Target URL must be a PostgreSQL URL (postgresql+asyncpg://...)")

    source_conn = sqlite3.connect(source_sqlite)
    source_conn.row_factory = sqlite3.Row
    source_tables = _list_source_tables(source_conn)
    summary: dict[str, int] = {}

    target_engine: AsyncEngine = create_async_engine(target_url, echo=False)
    try:
        async with target_engine.begin() as target_conn:
            await _create_target_schema(target_conn)
            if truncate:
                await _truncate_target_tables(target_conn)

            for table in Base.metadata.sorted_tables:
                if table.name not in source_tables:
                    summary[table.name] = 0
                    continue

                source_columns = _list_source_columns(source_conn, table.name)
                writable_columns = [
                    column for column in table.columns if column.name in source_columns
                ]
                if not writable_columns:
                    summary[table.name] = 0
                    continue

                inserted = 0
                column_names = [column.name for column in writable_columns]
                for batch in _iter_source_rows(
                    source_conn,
                    table_name=table.name,
                    columns=column_names,
                    batch_size=batch_size,
                ):
                    payload: list[dict[str, Any]] = []
                    for raw_row in batch:
                        normalized_row = {
                            column.name: _normalize_value(column, raw_row[column.name])
                            for column in writable_columns
                        }
                        payload.append(normalized_row)
                    if payload:
                        await target_conn.execute(sa.insert(table), payload)
                        inserted += len(payload)
                summary[table.name] = inserted

            await _sync_postgres_sequences(target_conn)
    finally:
        source_conn.close()
        await target_engine.dispose()

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate data from a SQLite database file into PostgreSQL."
    )
    parser.add_argument(
        "--source-sqlite",
        type=Path,
        default=PROJECT_ROOT / "db.sqlite3",
        help="Path to source SQLite database.",
    )
    parser.add_argument(
        "--target-url",
        required=True,
        help="Target SQLAlchemy URL. Example: postgresql+asyncpg://user:pass@host:5432/dbname",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of rows inserted per batch per table.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Delete all rows in target tables before importing.",
    )
    parser.add_argument(
        "--allow-non-postgres",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


async def _run() -> int:
    args = parse_args()
    try:
        summary = await migrate_sqlite_to_database(
            source_sqlite=args.source_sqlite.resolve(),
            target_url=args.target_url,
            truncate=args.truncate,
            batch_size=args.batch_size,
            allow_non_postgres=args.allow_non_postgres,
        )
    except Exception as exc:
        print(f"[ERROR] Migration failed: {exc}")
        return 1

    print("Migration finished successfully.")
    for table_name, count in summary.items():
        print(f"- {table_name}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
