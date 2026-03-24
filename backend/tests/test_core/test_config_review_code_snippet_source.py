from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import get_settings


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    [
        ("line", "line"),
        ("LINE", "line"),
        ("llm", "llm"),
        (" LLM ", "llm"),
    ],
)
def test_review_code_snippet_source_is_normalized(
    monkeypatch: pytest.MonkeyPatch,
    raw_value: str,
    expected: str,
) -> None:
    monkeypatch.setenv("REVIEW_CODE_SNIPPET_SOURCE", raw_value)
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.REVIEW_CODE_SNIPPET_SOURCE == expected
    get_settings.cache_clear()


def test_review_code_snippet_source_rejects_invalid_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("REVIEW_CODE_SNIPPET_SOURCE", "invalid")
    get_settings.cache_clear()
    with pytest.raises(ValidationError):
        get_settings()
    get_settings.cache_clear()
