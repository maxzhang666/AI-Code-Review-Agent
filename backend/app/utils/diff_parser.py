from __future__ import annotations

import re


_DIFF_BLOCK_RE = re.compile(r"@@ -\d+,\d+ \+\d+,\d+ @@.*?(?=\n@@|\Z)", re.DOTALL)
_RANGE_RE = re.compile(r"@@ -\d+(,\d+)? \+(\d+)(,\d+)? @@")


def parse_diff_content(diff_content: str) -> str:
    filtered = re.sub(r"(^-.*\n)|(^@@.*\n)", "", diff_content, flags=re.MULTILINE)
    return "\n".join(
        line[1:] if line.startswith("+") else line
        for line in filtered.split("\n")
    )


def extract_diffs(diff_content: str) -> list[str]:
    return _DIFF_BLOCK_RE.findall(diff_content)


def extract_diff_line_range(diff_content: str) -> list[int]:
    result: list[int] = []
    for line in diff_content.split("\n"):
        if not line.startswith("@@"):
            continue
        m = _RANGE_RE.match(line)
        if not m:
            continue
        start = int(m.group(2))
        result.append(start)
        end = start + int(m.group(3)[1:]) - 1 if m.group(3) else start
        result.append(end)
    return result
