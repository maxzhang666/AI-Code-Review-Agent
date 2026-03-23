from __future__ import annotations

from pathlib import Path

from app.config import Settings


def test_settings_env_file_uses_absolute_project_path() -> None:
    env_file = Settings.model_config.get("env_file")
    assert env_file is not None
    env_path = Path(str(env_file))
    assert env_path.is_absolute()
    assert env_path.name == ".env"
