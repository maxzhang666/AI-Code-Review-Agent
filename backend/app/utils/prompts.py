from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

PROMPT_POLICY_STRATEGY_OVERRIDE_ALLOWED_SCHEMA_LOCKED = "strategy_override_allowed_schema_locked"

IMMUTABLE_REVIEW_OUTPUT_CONTRACT = """\
【不可变输出协议（必须遵守）】
你只能输出纯 JSON（禁止 Markdown、禁止代码块、禁止额外解释）。
顶层字段必须包含：score、summary、highlights、issues。
score 必须是 0~100 整数；summary 必须是字符串；highlights 必须是字符串数组。
issues 必须是数组，每一项需包含：severity、category、file、line、description、suggestion、code_snippet。
若与任何上文指令冲突，以本协议为准。"""

_CONFLICT_PATTERNS = (
    re.compile(r"忽略.{0,20}(以上|之前|上述)?.{0,20}(指令|要求|提示|约束)"),
    re.compile(r"ignore.{0,20}(above|previous)?.{0,20}(instruction|requirement|prompt|constraint)", re.IGNORECASE),
    re.compile(r"(输出|返回).{0,10}(markdown|md|代码块)", re.IGNORECASE),
    re.compile(r"(不要|禁止|非).{0,10}(json|结构化)"),
    re.compile(r"(not|without|non).{0,10}(json|structured)", re.IGNORECASE),
)


@dataclass(frozen=True)
class PromptComposeResult:
    prompt: str
    policy: str
    conflict_detected: bool


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def detect_prompt_conflict(custom_prompt: Any) -> bool:
    custom = _normalize_text(custom_prompt)
    if not custom:
        return False
    return any(pattern.search(custom) for pattern in _CONFLICT_PATTERNS)


def compose_review_prompt(base_prompt: str, custom_prompt: Any) -> PromptComposeResult:
    base = _normalize_text(base_prompt)
    custom = _normalize_text(custom_prompt)
    conflict_detected = detect_prompt_conflict(custom)

    parts: list[str] = []
    if base:
        parts.append(base)
    if custom:
        parts.append(
            "【项目级审查策略补充】\n"
            "以下内容可补充或调整审查策略，但不得改变输出协议：\n"
            f"{custom}"
        )
    parts.append(IMMUTABLE_REVIEW_OUTPUT_CONTRACT)

    return PromptComposeResult(
        prompt="\n\n".join(item for item in parts if item),
        policy=PROMPT_POLICY_STRATEGY_OVERRIDE_ALLOWED_SCHEMA_LOCKED,
        conflict_detected=conflict_detected,
    )
