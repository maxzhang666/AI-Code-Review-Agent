from __future__ import annotations

from dataclasses import dataclass
import re


_PREFIX_PATTERN = re.compile(r"^\s*/cra\b", re.IGNORECASE)
_ACTION_PATTERN = re.compile(r"^(ignore|reopen|help)\b", re.IGNORECASE)
_REASON_PATTERN = re.compile(r"\breason\s*[：:]\s*", re.IGNORECASE)


class CommandParseError(ValueError):
    pass


@dataclass(frozen=True, eq=True)
class ParsedCommand:
    action: str
    issue_id: str | None
    reason: str | None


def parse_mr_feedback_command(raw: str) -> ParsedCommand | None:
    if not isinstance(raw, str):
        return None

    text = raw.strip()
    if not text:
        return None

    if not _PREFIX_PATTERN.match(text):
        return None

    body = _PREFIX_PATTERN.sub("", text, count=1).strip()
    if not body:
        raise CommandParseError("Missing action")

    action_match = _ACTION_PATTERN.match(body)
    if action_match is None:
        raise CommandParseError("Unsupported action")

    action = action_match.group(1).lower()
    rest = body[action_match.end():].strip()

    if action == "help":
        return ParsedCommand(action="help", issue_id=None, reason=None)

    reason_match = _REASON_PATTERN.search(rest)
    if reason_match is None:
        raise CommandParseError("Missing reason")

    issue_part = rest[:reason_match.start()].strip()
    if not issue_part:
        raise CommandParseError("Missing issue_id")

    issue_id = issue_part.split()[0].strip()
    if not issue_id:
        raise CommandParseError("Missing issue_id")

    reason = rest[reason_match.end():].strip()
    if not reason:
        raise CommandParseError("Missing reason")

    return ParsedCommand(action=action, issue_id=issue_id, reason=reason)

