from __future__ import annotations

import pytest

from app.services.mr_feedback import CommandParseError, ParsedCommand, parse_mr_feedback_command


def test_parse_ignore_command_with_reason() -> None:
    parsed = parse_mr_feedback_command("/cra ignore I-12 reason: 历史包袱，本次不处理")

    assert parsed == ParsedCommand(action="ignore", issue_id="I-12", reason="历史包袱，本次不处理")


def test_parse_reopen_command_with_multiline_reason() -> None:
    parsed = parse_mr_feedback_command(
        "/cra reopen I-9 reason: 已进入重构范围\n并且本周排期可覆盖"
    )

    assert parsed == ParsedCommand(
        action="reopen",
        issue_id="I-9",
        reason="已进入重构范围\n并且本周排期可覆盖",
    )


def test_parse_help_command() -> None:
    parsed = parse_mr_feedback_command("  /cra help  ")

    assert parsed == ParsedCommand(action="help", issue_id=None, reason=None)


def test_non_command_returns_none() -> None:
    assert parse_mr_feedback_command("LGTM，合并吧") is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("/cra ignore I-12", "Missing reason"),
        ("/cra ignore reason: xxx", "Missing issue_id"),
        ("/cra reopen I-7", "Missing reason"),
        ("/cra unknown I-7 reason: x", "Unsupported action"),
    ],
)
def test_invalid_command_raises_parse_error(raw: str, expected: str) -> None:
    with pytest.raises(CommandParseError) as exc_info:
        parse_mr_feedback_command(raw)

    assert expected in str(exc_info.value)

