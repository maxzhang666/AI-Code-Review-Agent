from __future__ import annotations

from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_system_log_files_list_returns_files(client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "app.log").write_text("line-1\nline-2\n", encoding="utf-8")
    (log_dir / "worker.log").write_text("worker-1\n", encoding="utf-8")

    monkeypatch.setenv("LOG_DIR", str(log_dir))
    from app.config import get_settings

    get_settings.cache_clear()

    response = await client.get("/api/system/log-files/")
    assert response.status_code == 200

    payload = response.json()
    assert payload["count"] == 2
    names = {item["name"] for item in payload["results"]}
    assert names == {"app.log", "worker.log"}
    for item in payload["results"]:
        assert ("+" in item["modified_at"]) or item["modified_at"].endswith("Z")


@pytest.mark.asyncio
async def test_system_log_file_content_returns_tail_lines_in_desc_order(
    client,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    content = "\n".join([f"line-{i}" for i in range(1, 8)]) + "\n"
    (log_dir / "app.log").write_text(content, encoding="utf-8")

    monkeypatch.setenv("LOG_DIR", str(log_dir))
    from app.config import get_settings

    get_settings.cache_clear()

    response = await client.get(
        "/api/system/log-files/content/",
        params={"filename": "app.log", "lines": 3},
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["file"] == "app.log"
    assert payload["total_lines"] == 7
    assert payload["returned_lines"] == 3
    assert payload["truncated"] is True
    assert payload["content"] == "line-7\nline-6\nline-5\n"


@pytest.mark.asyncio
async def test_system_log_file_content_rejects_path_traversal(client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("LOG_DIR", str(log_dir))
    from app.config import get_settings

    get_settings.cache_clear()

    response = await client.get(
        "/api/system/log-files/content/",
        params={"filename": "../secret.txt"},
    )
    assert response.status_code == 400
