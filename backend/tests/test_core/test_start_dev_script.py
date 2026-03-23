from __future__ import annotations

from pathlib import Path


def test_start_dev_script_exists_and_enables_reload() -> None:
    path = Path("start-dev.sh")
    assert path.exists()
    content = path.read_text(encoding="utf-8")
    assert "UVICORN_RELOAD=1" in content
    assert "exec ./start.sh" in content
