from __future__ import annotations

from app.database import _PENDING_COLUMNS


def test_boolean_pending_columns_use_boolean_literals_for_defaults() -> None:
    for _table, _column, ddl in _PENDING_COLUMNS:
        normalized = ddl.strip().upper()
        if "BOOLEAN" not in normalized:
            continue
        assert "DEFAULT 0" not in normalized
        assert "DEFAULT 1" not in normalized

