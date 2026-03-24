from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.logging import get_logger
from app.llm import llm_router
from app.llm.types import LLMRequest
from app.utils.prompts import compose_review_prompt
from .chunking import (
    build_chunk_prompt,
    build_file_units,
    build_reduce_prompt,
    compute_input_budget,
    estimate_tokens,
    plan_chunks,
    resolve_chunk_max_tokens,
    resolve_max_tokens,
    resolve_positive_int,
    resolve_ratio,
)
from .filtering import (
    filter_changes,
    load_project_config,
)
from .parser import ReviewResultParser
from .tracing import (
    build_empty_llm_trace,
    build_final_llm_trace,
    build_overflow_only_result,
    extract_response_trace,
    is_structured_review_result,
    merge_map_outputs,
)


class ReviewService:
    _TOKEN_ESTIMATE_DIVISOR = 4
    _DEFAULT_CONTEXT_WINDOW = 128000
    _DEFAULT_PROMPT_RESERVE_TOKENS = 3000
    _DEFAULT_INPUT_SAFETY_RATIO = 0.75
    _MIN_MAX_TOKENS = 256
    _MAX_ISSUES_IN_FALLBACK = 100
    _MAX_HIGHLIGHTS_IN_FALLBACK = 10

    def __init__(self, request_id: str | None = None) -> None:
        self._settings = get_settings()
        self._request_id = request_id
        self._logger = get_logger(__name__, request_id)

    async def review_merge_request(
        self,
        changes: list[dict[str, Any]],
        payload: dict[str, Any],
        db: AsyncSession,
    ) -> dict[str, Any]:
        project_data = payload.get("project")
        project_id: int | None = None
        if isinstance(project_data, dict):
            value = project_data.get("id")
            if isinstance(value, int):
                project_id = value
        if project_id is None:
            value = payload.get("project_id")
            if isinstance(value, int):
                project_id = value

        exclude_file_types, ignore_patterns = await load_project_config(
            settings=self._settings,
            project_id=project_id,
            db=db,
        )
        filtered_changes, filter_summary = await filter_changes(changes, exclude_file_types, ignore_patterns)

        if not filtered_changes:
            return {
                "content": "没有需要审查的代码变更",
                "score": None,
                "files_reviewed": [],
                "filter_summary": filter_summary,
            }

        provider = await llm_router.resolve_provider(project_id or 0, db)
        provider_config_raw = getattr(provider, "config_data", {})
        provider_config = provider_config_raw if isinstance(provider_config_raw, dict) else {}
        max_tokens = resolve_max_tokens(provider_config.get("max_tokens"), default=20480)

        context_window_tokens = resolve_positive_int(
            provider_config.get("context_window") or provider_config.get("max_context_tokens"),
            default=self._DEFAULT_CONTEXT_WINDOW,
        )
        reserve_tokens = resolve_positive_int(
            provider_config.get("prompt_reserve_tokens"),
            default=self._DEFAULT_PROMPT_RESERVE_TOKENS,
        )
        input_safety_ratio = resolve_ratio(
            provider_config.get("input_safety_ratio"),
            default=self._DEFAULT_INPUT_SAFETY_RATIO,
        )
        input_budget_tokens = compute_input_budget(
            context_window_tokens=context_window_tokens,
            max_tokens=max_tokens,
            reserve_tokens=reserve_tokens,
            input_safety_ratio=input_safety_ratio,
        )

        prompt_composition = compose_review_prompt(self._settings.GPT_MESSAGE, payload.get("custom_prompt"))
        system_message = prompt_composition.prompt

        file_units = build_file_units(
            filtered_changes,
            token_estimate_divisor=self._TOKEN_ESTIMATE_DIVISOR,
        )
        chunk_plan = plan_chunks(
            file_units,
            input_budget_tokens=input_budget_tokens,
            token_estimate_divisor=self._TOKEN_ESTIMATE_DIVISOR,
        )

        map_calls: list[dict[str, Any]] = []
        map_outputs: list[dict[str, Any]] = []
        map_duration_total = 0
        map_prompt_tokens_total = 0
        map_completion_tokens_total = 0
        map_reasoning_tokens_total = 0
        map_contents: list[str] = []
        reduce_call: dict[str, Any] | None = None

        if not chunk_plan["chunks"]:
            fallback = build_overflow_only_result(chunk_plan["overflow_files"])
            fallback["files_reviewed"] = [item.get("file_path", "") for item in file_units]
            fallback["llm_provider"] = provider.name
            fallback["llm_model"] = str(provider_config.get("model") or provider.name)
            fallback["filter_summary"] = filter_summary
            fallback["llm_trace"] = build_empty_llm_trace(
                provider_name=provider.name,
                provider_protocol=provider.protocol,
                provider_model=str(provider_config.get("model") or ""),
                max_tokens=max_tokens,
                system_message=system_message,
                prompt_policy=prompt_composition.policy,
                conflict_detected=prompt_composition.conflict_detected,
                context_window_tokens=context_window_tokens,
                reserve_tokens=reserve_tokens,
                input_safety_ratio=input_safety_ratio,
                input_budget_tokens=input_budget_tokens,
                total_estimated_input_tokens=chunk_plan["total_estimated_tokens"],
                estimated_map_request_count=chunk_plan["estimated_map_request_count"],
                overflow_files=chunk_plan["overflow_files"],
                chunk_plan=chunk_plan["chunks_meta"],
                response_model=str(provider_config.get("model") or provider.name),
                response_content=str(fallback.get("content") or ""),
            )
            return fallback

        total_chunks = len(chunk_plan["chunks"])
        for idx, chunk in enumerate(chunk_plan["chunks"], start=1):
            chunk_prompt = build_chunk_prompt(
                chunk_context=chunk["context"],
                chunk_index=idx,
                chunk_count=total_chunks,
            )
            chunk_max_tokens = resolve_chunk_max_tokens(
                chunk_tokens=chunk["estimated_tokens"],
                context_window_tokens=context_window_tokens,
                reserve_tokens=reserve_tokens,
                input_safety_ratio=input_safety_ratio,
                default_max_tokens=max_tokens,
                min_max_tokens=self._MIN_MAX_TOKENS,
            )
            if chunk_max_tokens <= 0:
                chunk_plan["overflow_files"].extend(chunk["files"])
                continue

            request_trace = {
                "chunk_index": idx,
                "chunk_count": total_chunks,
                "file_count": len(chunk["files"]),
                "files": chunk["files"],
                "estimated_input_tokens": chunk["estimated_tokens"],
                "max_tokens": chunk_max_tokens,
                "prompt_length": len(chunk_prompt),
                "prompt_preview": chunk_prompt,
                "prompt_preview_truncated": False,
                "system_message_length": len(system_message),
                "system_message_preview": system_message,
                "system_message_preview_truncated": False,
                "prompt_policy": prompt_composition.policy,
                "conflict_detected": prompt_composition.conflict_detected,
            }

            llm_request = LLMRequest(
                prompt=chunk_prompt,
                system_message=system_message,
                max_tokens=chunk_max_tokens,
            )
            self._logger.info(
                "llm_chunk_call_start",
                provider=provider.name,
                protocol=provider.protocol,
                chunk_index=idx,
                chunk_count=total_chunks,
                file_count=len(chunk["files"]),
            )
            llm_response = await llm_router.review(provider, llm_request)
            self._logger.info(
                "llm_chunk_call_done",
                model=llm_response.model,
                content_len=len(llm_response.content),
                chunk_index=idx,
                chunk_count=total_chunks,
            )

            response_trace = extract_response_trace(llm_response)
            parsed = ReviewResultParser.parse(llm_response.content)
            map_outputs.append(
                {
                    "chunk_index": idx,
                    "files": chunk["files"],
                    "score": parsed.get("score"),
                    "summary": parsed.get("summary") or "",
                    "highlights": parsed.get("highlights") or [],
                    "issues": parsed.get("issues") or [],
                    "content": llm_response.content,
                }
            )
            map_contents.append(str(llm_response.content or ""))
            map_calls.append(
                {
                    "request": request_trace,
                    "response": response_trace,
                }
            )
            map_duration_total += int(response_trace.get("duration_ms") or 0)
            map_prompt_tokens_total += int(response_trace.get("prompt_tokens") or 0)
            map_completion_tokens_total += int(response_trace.get("completion_tokens") or 0)
            map_reasoning_tokens_total += int(response_trace.get("reasoning_tokens") or 0)

        if not map_calls:
            fallback = build_overflow_only_result(chunk_plan["overflow_files"])
            fallback["files_reviewed"] = [item.get("file_path", "") for item in file_units]
            fallback["llm_provider"] = provider.name
            fallback["llm_model"] = str(provider_config.get("model") or provider.name)
            fallback["filter_summary"] = filter_summary
            fallback["llm_trace"] = build_empty_llm_trace(
                provider_name=provider.name,
                provider_protocol=provider.protocol,
                provider_model=str(provider_config.get("model") or ""),
                max_tokens=max_tokens,
                system_message=system_message,
                prompt_policy=prompt_composition.policy,
                conflict_detected=prompt_composition.conflict_detected,
                context_window_tokens=context_window_tokens,
                reserve_tokens=reserve_tokens,
                input_safety_ratio=input_safety_ratio,
                input_budget_tokens=input_budget_tokens,
                total_estimated_input_tokens=chunk_plan["total_estimated_tokens"],
                estimated_map_request_count=chunk_plan["estimated_map_request_count"],
                overflow_files=chunk_plan["overflow_files"],
                chunk_plan=chunk_plan["chunks_meta"],
                response_model=str(provider_config.get("model") or provider.name),
                response_content=str(fallback.get("content") or ""),
            )
            return fallback

        reduce_required = len(map_outputs) > 1
        final_content = map_contents[0]
        final_parsed = ReviewResultParser.parse(final_content)
        final_response_trace = map_calls[0]["response"] if map_calls else {}
        llm_model = str(final_response_trace.get("model") or provider_config.get("model") or provider.name)
        reduce_request_count = 0
        reduce_content = ""
        if reduce_required:
            reduce_prompt = build_reduce_prompt(map_outputs, chunk_plan["overflow_files"])
            reduce_request = LLMRequest(
                prompt=reduce_prompt,
                system_message=system_message,
                max_tokens=max_tokens,
            )
            self._logger.info("llm_reduce_call_start", provider=provider.name, protocol=provider.protocol)
            reduce_response = await llm_router.review(provider, reduce_request)
            self._logger.info(
                "llm_reduce_call_done",
                model=reduce_response.model,
                content_len=len(reduce_response.content),
            )

            reduce_response_trace = extract_response_trace(reduce_response)
            reduce_parsed = ReviewResultParser.parse(reduce_response.content)
            reduce_content = str(reduce_response.content or "")
            reduce_call = {
                "request": {
                    "chunk_index": len(map_calls) + 1,
                    "chunk_count": len(map_calls) + 1,
                    "file_count": 0,
                    "files": [],
                    "estimated_input_tokens": estimate_tokens(
                        reduce_prompt,
                        token_estimate_divisor=self._TOKEN_ESTIMATE_DIVISOR,
                    ),
                    "max_tokens": max_tokens,
                    "prompt_length": len(reduce_prompt),
                    "prompt_preview": reduce_prompt,
                    "prompt_preview_truncated": False,
                    "system_message_length": len(system_message),
                    "system_message_preview": system_message,
                    "system_message_preview_truncated": False,
                    "prompt_policy": prompt_composition.policy,
                    "conflict_detected": prompt_composition.conflict_detected,
                },
                "response": reduce_response_trace,
            }
            reduce_request_count = 1
            llm_model = str(reduce_response_trace.get("model") or llm_model)

            if is_structured_review_result(reduce_parsed):
                final_content = reduce_content
                final_parsed = reduce_parsed
                final_response_trace = reduce_response_trace
            else:
                merged = merge_map_outputs(
                    map_outputs,
                    chunk_plan["overflow_files"],
                    max_issues_in_fallback=self._MAX_ISSUES_IN_FALLBACK,
                    max_highlights_in_fallback=self._MAX_HIGHLIGHTS_IN_FALLBACK,
                )
                final_content = json.dumps(merged, ensure_ascii=False)
                final_parsed = merged
                # Keep metrics from reduce call for observability, even when fallback kicks in.
                final_response_trace = reduce_response_trace
        else:
            final_parsed = map_outputs[0]
            final_parsed = {
                "content": final_content,
                "score": final_parsed.get("score"),
                "summary": str(final_parsed.get("summary") or ""),
                "highlights": list(final_parsed.get("highlights") or []),
                "issues": list(final_parsed.get("issues") or []),
            }

        if chunk_plan["overflow_files"]:
            overflow_note = f"另有 {len(chunk_plan['overflow_files'])} 个超大文件未纳入自动审查，请人工补充审查。"
            summary_text = str(final_parsed.get("summary") or "").strip()
            final_parsed["summary"] = f"{summary_text} {overflow_note}".strip() if summary_text else overflow_note

        total_duration_ms = map_duration_total + int(final_response_trace.get("duration_ms") or 0)
        response_content_preview = str(
            final_response_trace.get("content_preview")
            or final_parsed.get("content")
            or final_content
            or ""
        )
        trace_prompt_preview = (
            reduce_call["request"]["prompt_preview"]
            if reduce_call
            else str(map_calls[0]["request"]["prompt_preview"])
        )
        llm_trace = build_final_llm_trace(
            provider_name=provider.name,
            provider_protocol=provider.protocol,
            provider_model=str(provider_config.get("model") or ""),
            max_tokens=max_tokens,
            prompt_preview=trace_prompt_preview,
            system_message=system_message,
            prompt_policy=prompt_composition.policy,
            conflict_detected=prompt_composition.conflict_detected,
            chunking_enabled=total_chunks > 1,
            context_window_tokens=context_window_tokens,
            reserve_tokens=reserve_tokens,
            input_safety_ratio=input_safety_ratio,
            input_budget_tokens=input_budget_tokens,
            total_estimated_input_tokens=chunk_plan["total_estimated_tokens"],
            estimated_map_request_count=chunk_plan["estimated_map_request_count"],
            actual_map_request_count=len(map_calls),
            reduce_request_count=reduce_request_count,
            overflow_files=chunk_plan["overflow_files"],
            chunk_plan=chunk_plan["chunks_meta"],
            map_calls=map_calls,
            reduce_call=reduce_call,
            llm_model=llm_model,
            total_duration_ms=total_duration_ms,
            final_content=str(final_content or ""),
            response_content_preview=response_content_preview,
            final_response_trace=final_response_trace,
            map_duration_ms_total=map_duration_total,
            map_prompt_tokens_total=map_prompt_tokens_total,
            map_completion_tokens_total=map_completion_tokens_total,
            map_reasoning_tokens_total=map_reasoning_tokens_total,
            map_outputs=map_outputs,
            reduce_content=reduce_content,
        )

        final_parsed["content"] = str(final_content or "")
        final_parsed["files_reviewed"] = [item.get("file_path", "") for item in file_units]
        final_parsed["llm_provider"] = provider.name
        final_parsed["llm_model"] = llm_model
        final_parsed["filter_summary"] = filter_summary
        final_parsed["llm_trace"] = llm_trace
        final_parsed["overflow_files"] = chunk_plan["overflow_files"]
        return final_parsed

    async def _load_project_config(
        self,
        project_id: int | None,
        db: AsyncSession,
    ) -> tuple[list[str], list[str]]:
        return await load_project_config(
            settings=self._settings,
            project_id=project_id,
            db=db,
        )
