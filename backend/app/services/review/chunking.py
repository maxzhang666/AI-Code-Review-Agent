from __future__ import annotations

import json
import math
from typing import Any


def resolve_max_tokens(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if parsed <= 0:
        return default
    return parsed


def resolve_positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return parsed if parsed > 0 else default


def resolve_ratio(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    if parsed <= 0.1:
        return default
    if parsed >= 0.95:
        return 0.95
    return parsed


def compute_input_budget(
    context_window_tokens: int,
    max_tokens: int,
    reserve_tokens: int,
    input_safety_ratio: float,
) -> int:
    remaining = max(context_window_tokens - max_tokens - reserve_tokens, 0)
    return max(int(math.floor(remaining * input_safety_ratio)), 1)


def estimate_tokens(text: str, token_estimate_divisor: int) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / token_estimate_divisor))


def build_file_units(
    changes: list[dict[str, Any]],
    *,
    token_estimate_divisor: int,
) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for change in changes:
        file_path = str(change.get("new_path") or change.get("old_path") or "unknown")
        diff = str(change.get("diff") or "")
        context = f"## 文件: {file_path}\n\n```diff\n{diff}\n```\n"
        units.append(
            {
                "file_path": file_path,
                "context": context,
                "estimated_tokens": estimate_tokens(context, token_estimate_divisor),
            }
        )
    return units


def plan_chunks(
    file_units: list[dict[str, Any]],
    input_budget_tokens: int,
    *,
    token_estimate_divisor: int,
) -> dict[str, Any]:
    chunks: list[dict[str, Any]] = []
    overflow_files: list[str] = []

    current_files: list[str] = []
    current_context_parts: list[str] = []
    current_tokens = 0
    chunkable_tokens_total = 0
    all_tokens_total = 0

    for unit in file_units:
        file_path = str(unit.get("file_path") or "unknown")
        context = str(unit.get("context") or "")
        token_est = int(unit.get("estimated_tokens") or 0)
        if token_est <= 0:
            token_est = estimate_tokens(context, token_estimate_divisor)
        all_tokens_total += token_est

        if token_est > input_budget_tokens:
            overflow_files.append(file_path)
            continue

        if current_files and current_tokens + token_est > input_budget_tokens:
            chunks.append(
                {
                    "files": current_files,
                    "context": "\n".join(current_context_parts),
                    "estimated_tokens": current_tokens,
                }
            )
            chunkable_tokens_total += current_tokens
            current_files = []
            current_context_parts = []
            current_tokens = 0

        current_files.append(file_path)
        current_context_parts.append(context)
        current_tokens += token_est

    if current_files:
        chunks.append(
            {
                "files": current_files,
                "context": "\n".join(current_context_parts),
                "estimated_tokens": current_tokens,
            }
        )
        chunkable_tokens_total += current_tokens

    estimated_map_requests = math.ceil(chunkable_tokens_total / max(input_budget_tokens, 1)) if chunkable_tokens_total > 0 else 0
    chunks_meta = [
        {
            "chunk_index": idx + 1,
            "file_count": len(chunk["files"]),
            "estimated_tokens": chunk["estimated_tokens"],
            "files": chunk["files"],
        }
        for idx, chunk in enumerate(chunks)
    ]
    return {
        "chunks": chunks,
        "chunks_meta": chunks_meta,
        "overflow_files": overflow_files,
        "total_estimated_tokens": all_tokens_total,
        "chunkable_estimated_tokens": chunkable_tokens_total,
        "estimated_map_request_count": estimated_map_requests,
    }


def resolve_chunk_max_tokens(
    chunk_tokens: int,
    context_window_tokens: int,
    reserve_tokens: int,
    input_safety_ratio: float,
    default_max_tokens: int,
    *,
    min_max_tokens: int,
) -> int:
    if chunk_tokens <= 0:
        return default_max_tokens

    base_budget = compute_input_budget(
        context_window_tokens=context_window_tokens,
        max_tokens=default_max_tokens,
        reserve_tokens=reserve_tokens,
        input_safety_ratio=input_safety_ratio,
    )
    if chunk_tokens <= base_budget:
        return default_max_tokens

    required_input_room = int(math.ceil(chunk_tokens / max(input_safety_ratio, 0.1)))
    candidate = context_window_tokens - reserve_tokens - required_input_room
    if candidate < min_max_tokens:
        return 0
    return min(default_max_tokens, candidate)


def build_chunk_prompt(chunk_context: str, chunk_index: int, chunk_count: int) -> str:
    return (
        f"你正在审查一个超大 MR 的分片 {chunk_index}/{chunk_count}。\n"
        "注意：文件不可拆分，本次请求只包含其中一部分完整文件。\n"
        "请仅根据当前分片中的代码变更给出严格审查结论，并按照约定 JSON 返回。\n\n"
        f"{chunk_context}"
    )


def build_reduce_prompt(map_outputs: list[dict[str, Any]], overflow_files: list[str]) -> str:
    payload = {
        "chunk_results": [
            {
                "chunk_index": item.get("chunk_index"),
                "files": item.get("files", []),
                "score": item.get("score"),
                "summary": item.get("summary"),
                "highlights": item.get("highlights", []),
                "issues": item.get("issues", []),
            }
            for item in map_outputs
        ],
        "overflow_files": overflow_files,
    }
    return (
        "请汇总以下多个代码分片审查结果，输出一个统一的最终审查 JSON。\n"
        "要求：\n"
        "1. 合并并去重 issues（同一 file+line+description 视为重复）。\n"
        "2. 对重复或冲突结论进行归并，给出单一最终建议。\n"
        "3. score 代表整体质量评分。\n"
        "4. 如果 overflow_files 非空，在 summary 中明确提示这些文件未自动审查。\n"
        "5. 只返回 JSON。\n\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )
