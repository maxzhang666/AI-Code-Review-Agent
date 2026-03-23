from __future__ import annotations

import re
from pathlib import Path


def _read_start_script() -> str:
    return Path("start.sh").read_text(encoding="utf-8")


def test_start_script_uses_exec_for_uvicorn_process() -> None:
    content = _read_start_script()
    assert re.search(r"^\s*exec\s+uvicorn\b", content, flags=re.MULTILINE)


def test_start_script_logs_database_url_environment() -> None:
    content = _read_start_script()
    assert "DATABASE_URL" in content


def test_start_script_supports_optional_reload_mode() -> None:
    content = _read_start_script()
    assert "UVICORN_RELOAD" in content
    assert "--reload" in content


def test_start_script_does_not_force_sqlite_fallback_in_shell() -> None:
    content = _read_start_script()
    assert 'DATABASE_URL="${DATABASE_URL:-sqlite+aiosqlite:///./db.sqlite3}"' not in content
