from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app.core.logging import configure_logging


def _reset_root_logger() -> tuple[list[logging.Handler], int]:
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level
    for handler in list(root.handlers):
        root.removeHandler(handler)
    return original_handlers, original_level


def _restore_root_logger(original_handlers: list[logging.Handler], original_level: int) -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        try:
            handler.close()
        except Exception:
            pass
    for handler in original_handlers:
        root.addHandler(handler)
    root.setLevel(original_level)


def test_configure_logging_uses_rotation_parameters(tmp_path: Path) -> None:
    original_handlers, original_level = _reset_root_logger()
    try:
        configure_logging(
            log_level="INFO",
            log_dir=str(tmp_path),
            max_bytes=1024,
            backup_count=3,
        )

        root = logging.getLogger()
        file_handler = next(
            (
                handler
                for handler in root.handlers
                if isinstance(handler, RotatingFileHandler)
            ),
            None,
        )
        assert file_handler is not None
        assert file_handler.maxBytes == 1024
        assert file_handler.backupCount == 3
    finally:
        _restore_root_logger(original_handlers, original_level)


def test_rotating_file_handler_rolls_and_keeps_latest_n(tmp_path: Path) -> None:
    original_handlers, original_level = _reset_root_logger()
    try:
        configure_logging(
            log_level="INFO",
            log_dir=str(tmp_path),
            max_bytes=256,
            backup_count=2,
        )
        logger = logging.getLogger("rotation-test")
        for i in range(200):
            logger.info("x" * 80 + f" #{i}")

        for handler in logging.getLogger().handlers:
            try:
                handler.flush()
            except Exception:
                pass

        log_files = sorted(path.name for path in tmp_path.glob("app.log*"))
        assert "app.log" in log_files
        assert "app.log.1" in log_files
        assert "app.log.2" in log_files
        assert len(log_files) <= 3
    finally:
        _restore_root_logger(original_handlers, original_level)

