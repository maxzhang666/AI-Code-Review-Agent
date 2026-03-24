from __future__ import annotations

import json
from typing import Any

from app.llm.types import LLMResponse
from .parser import ReviewResultParser


def extract_response_trace(llm_response: LLMResponse) -> dict[str, Any]:
    raw_response_text = ""
    raw_response = llm_response.raw_response
    if isinstance(raw_response, dict):
        raw_response_text = json.dumps(raw_response, ensure_ascii=False)

    finish_reason = ""
    prompt_tokens = 0
    completion_tokens = 0
    reasoning_tokens = 0
    if isinstance(raw_response, dict):
        choices_raw = raw_response.get("choices")
        if isinstance(choices_raw, list) and choices_raw and isinstance(choices_raw[0], dict):
            finish_reason = str(choices_raw[0].get("finish_reason") or "")
        usage_raw = raw_response.get("usage")
        usage = usage_raw if isinstance(usage_raw, dict) else {}
        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        details_raw = usage.get("completion_tokens_details")
        details = details_raw if isinstance(details_raw, dict) else {}
        reasoning_tokens = int(details.get("reasoning_tokens") or 0)

    content_preview = llm_response.content
    content_from_raw_fallback = False
    if not content_preview and raw_response_text:
        content_preview = raw_response_text
        content_from_raw_fallback = True

    return {
        "model": llm_response.model,
        "duration_ms": llm_response.duration_ms,
        "content_length": len(llm_response.content),
        "content_preview": content_preview,
        "content_preview_truncated": False,
        "content_from_raw_fallback": content_from_raw_fallback,
        "raw_response_length": len(raw_response_text) if raw_response_text else 0,
        "raw_response_preview": raw_response_text if content_from_raw_fallback else "",
        "raw_response_preview_truncated": False,
        "finish_reason": finish_reason,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "reasoning_tokens": reasoning_tokens,
    }


def is_structured_review_result(parsed: dict[str, Any]) -> bool:
    if not isinstance(parsed, dict):
        return False
    has_summary = bool(str(parsed.get("summary") or "").strip())
    issues = parsed.get("issues")
    has_issues = isinstance(issues, list) and len(issues) > 0
    highlights = parsed.get("highlights")
    has_highlights = isinstance(highlights, list) and len(highlights) > 0
    has_score = isinstance(parsed.get("score"), int)
    return has_summary or has_issues or has_highlights or has_score


def merge_map_outputs(
    map_outputs: list[dict[str, Any]],
    overflow_files: list[str],
    *,
    max_issues_in_fallback: int,
    max_highlights_in_fallback: int,
) -> dict[str, Any]:
    scores: list[int] = []
    highlights: list[str] = []
    highlights_seen: set[str] = set()
    issues: list[dict[str, Any]] = []
    issue_seen: set[str] = set()
    summaries: list[str] = []

    for item in map_outputs:
        score = item.get("score")
        if isinstance(score, int):
            scores.append(max(0, min(100, score)))

        summary = str(item.get("summary") or "").strip()
        if summary:
            summaries.append(summary)

        for h in item.get("highlights") or []:
            text = str(h or "").strip()
            if not text or text in highlights_seen:
                continue
            highlights_seen.add(text)
            highlights.append(text)
            if len(highlights) >= max_highlights_in_fallback:
                break

        for raw_issue in item.get("issues") or []:
            issue = ReviewResultParser._validate_issue(raw_issue)
            if issue is None:
                continue
            dedup_key = (
                f"{issue.get('file')}|{issue.get('line')}|"
                f"{issue.get('description')}|{issue.get('category')}"
            )
            if dedup_key in issue_seen:
                continue
            issue_seen.add(dedup_key)
            issues.append(issue)
            if len(issues) >= max_issues_in_fallback:
                break

    merged_score = round(sum(scores) / len(scores)) if scores else None
    merged_summary = "；".join(summaries[:3]) if summaries else "分片审查完成，已自动合并结果。"
    if overflow_files:
        merged_summary = f"{merged_summary} 另有 {len(overflow_files)} 个超大文件未自动审查，请人工补充审查。"

    merged = {
        "content": "",
        "score": merged_score,
        "summary": merged_summary,
        "highlights": highlights,
        "issues": issues,
    }
    merged["content"] = json.dumps(
        {
            "score": merged["score"],
            "summary": merged["summary"],
            "highlights": merged["highlights"],
            "issues": merged["issues"],
        },
        ensure_ascii=False,
    )
    return merged


def build_overflow_only_result(overflow_files: list[str]) -> dict[str, Any]:
    return {
        "content": "自动审查失败：所有文件均超出单次请求预算，请调大上下文窗口或人工审查。",
        "score": None,
        "summary": (
            f"共有 {len(overflow_files)} 个文件超出单次请求预算，"
            "系统未执行自动审查。请调整模型上下文窗口或拆分 MR。"
        ),
        "highlights": [],
        "issues": [],
        "overflow_files": overflow_files,
    }


def build_empty_llm_trace(
    *,
    provider_name: str,
    provider_protocol: str,
    provider_model: str,
    max_tokens: int,
    system_message: str,
    prompt_policy: str,
    conflict_detected: bool,
    context_window_tokens: int,
    reserve_tokens: int,
    input_safety_ratio: float,
    input_budget_tokens: int,
    total_estimated_input_tokens: int,
    estimated_map_request_count: int,
    overflow_files: list[str],
    chunk_plan: list[dict[str, Any]],
    response_model: str,
    response_content: str,
) -> dict[str, Any]:
    return {
        "request": {
            "provider": provider_name,
            "protocol": provider_protocol,
            "model": provider_model,
            "max_tokens": max_tokens,
            "prompt_length": 0,
            "prompt_preview": "",
            "prompt_preview_truncated": False,
            "system_message_length": len(system_message),
            "system_message_preview": system_message,
            "system_message_preview_truncated": False,
            "prompt_policy": prompt_policy,
            "conflict_detected": conflict_detected,
            "chunking_enabled": True,
            "context_window_tokens": context_window_tokens,
            "reserve_tokens": reserve_tokens,
            "input_safety_ratio": input_safety_ratio,
            "input_budget_tokens": input_budget_tokens,
            "total_estimated_input_tokens": total_estimated_input_tokens,
            "estimated_map_request_count": estimated_map_request_count,
            "actual_map_request_count": 0,
            "reduce_request_count": 0,
            "total_request_count": 0,
            "overflow_file_count": len(overflow_files),
            "overflow_files": json.dumps(overflow_files, ensure_ascii=False, indent=2),
            "chunk_plan": json.dumps(chunk_plan, ensure_ascii=False, indent=2),
            "map_calls": "[]",
            "reduce_call": "-",
        },
        "response": {
            "model": response_model,
            "duration_ms": 0,
            "content_length": len(response_content or ""),
            "content_preview": str(response_content or ""),
            "content_preview_truncated": False,
            "content_from_raw_fallback": False,
            "raw_response_length": 0,
            "raw_response_preview": "",
            "raw_response_preview_truncated": False,
            "finish_reason": "",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "reasoning_tokens": 0,
            "map_duration_ms_total": 0,
            "map_prompt_tokens_total": 0,
            "map_completion_tokens_total": 0,
            "map_reasoning_tokens_total": 0,
            "total_request_count": 0,
            "map_outputs": "[]",
        },
    }


def build_final_llm_trace(
    *,
    provider_name: str,
    provider_protocol: str,
    provider_model: str,
    max_tokens: int,
    prompt_preview: str,
    system_message: str,
    prompt_policy: str,
    conflict_detected: bool,
    chunking_enabled: bool,
    context_window_tokens: int,
    reserve_tokens: int,
    input_safety_ratio: float,
    input_budget_tokens: int,
    total_estimated_input_tokens: int,
    estimated_map_request_count: int,
    actual_map_request_count: int,
    reduce_request_count: int,
    overflow_files: list[str],
    chunk_plan: list[dict[str, Any]],
    map_calls: list[dict[str, Any]],
    reduce_call: dict[str, Any] | None,
    llm_model: str,
    total_duration_ms: int,
    final_content: str,
    response_content_preview: str,
    final_response_trace: dict[str, Any],
    map_duration_ms_total: int,
    map_prompt_tokens_total: int,
    map_completion_tokens_total: int,
    map_reasoning_tokens_total: int,
    map_outputs: list[dict[str, Any]],
    reduce_content: str,
) -> dict[str, Any]:
    total_request_count = actual_map_request_count + reduce_request_count
    return {
        "request": {
            "provider": provider_name,
            "protocol": provider_protocol,
            "model": provider_model,
            "max_tokens": max_tokens,
            "prompt_length": len(prompt_preview),
            "prompt_preview": prompt_preview,
            "prompt_preview_truncated": False,
            "system_message_length": len(system_message),
            "system_message_preview": system_message,
            "system_message_preview_truncated": False,
            "prompt_policy": prompt_policy,
            "conflict_detected": conflict_detected,
            "chunking_enabled": chunking_enabled,
            "context_window_tokens": context_window_tokens,
            "reserve_tokens": reserve_tokens,
            "input_safety_ratio": input_safety_ratio,
            "input_budget_tokens": input_budget_tokens,
            "total_estimated_input_tokens": total_estimated_input_tokens,
            "estimated_map_request_count": estimated_map_request_count,
            "actual_map_request_count": actual_map_request_count,
            "reduce_request_count": reduce_request_count,
            "total_request_count": total_request_count,
            "overflow_file_count": len(overflow_files),
            "overflow_files": json.dumps(overflow_files, ensure_ascii=False, indent=2),
            "chunk_plan": json.dumps(chunk_plan, ensure_ascii=False, indent=2),
            "map_calls": json.dumps(map_calls, ensure_ascii=False, indent=2),
            "reduce_call": json.dumps(reduce_call, ensure_ascii=False, indent=2) if reduce_call else "-",
        },
        "response": {
            "model": llm_model,
            "duration_ms": total_duration_ms,
            "content_length": len(str(final_content or "")),
            "content_preview": response_content_preview,
            "content_preview_truncated": False,
            "content_from_raw_fallback": bool(final_response_trace.get("content_from_raw_fallback")),
            "raw_response_length": int(final_response_trace.get("raw_response_length") or 0),
            "raw_response_preview": str(final_response_trace.get("raw_response_preview") or ""),
            "raw_response_preview_truncated": False,
            "finish_reason": str(final_response_trace.get("finish_reason") or ""),
            "prompt_tokens": int(final_response_trace.get("prompt_tokens") or 0),
            "completion_tokens": int(final_response_trace.get("completion_tokens") or 0),
            "reasoning_tokens": int(final_response_trace.get("reasoning_tokens") or 0),
            "map_duration_ms_total": map_duration_ms_total,
            "map_prompt_tokens_total": map_prompt_tokens_total,
            "map_completion_tokens_total": map_completion_tokens_total,
            "map_reasoning_tokens_total": map_reasoning_tokens_total,
            "total_request_count": total_request_count,
            "map_outputs": json.dumps(map_outputs, ensure_ascii=False, indent=2),
            "reduce_content": reduce_content,
        },
    }
