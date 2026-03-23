from __future__ import annotations

import fnmatch
import json
import math
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.logging import get_logger
from app.llm import llm_router
from app.llm.types import LLMRequest, LLMResponse
from app.models import Project


class ReviewResultParser:
    SCORE_PATTERN = re.compile(r"代码评分[:：\s]*(\d+)")
    JSON_BLOCK_PATTERN = re.compile(r"```(?:json)?\s*\n?(.*?)\n?\s*```", re.DOTALL)

    @classmethod
    def _extract_json(cls, content: str) -> dict[str, Any] | None:
        if not content:
            return None
        text = content.strip()
        # Try direct JSON parse
        if text.startswith("{"):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        # Try extracting from ```json ... ``` block
        match = cls.JSON_BLOCK_PATTERN.search(text)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        # Try finding first { ... } block
        start = text.find("{")
        if start != -1:
            depth = 0
            for i in range(start, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start : i + 1])
                        except json.JSONDecodeError:
                            break
        return None

    @classmethod
    def _validate_issue(cls, item: Any) -> dict[str, Any] | None:
        if not isinstance(item, dict):
            return None
        severity = str(item.get("severity") or "medium").lower()
        if severity not in ("high", "medium", "low"):
            severity = "medium"
        return {
            "severity": severity,
            "category": str(item.get("category") or "质量"),
            "file": str(item.get("file") or ""),
            "line": item.get("line") if isinstance(item.get("line"), int) else None,
            "description": str(item.get("description") or ""),
            "suggestion": str(item.get("suggestion") or ""),
        }

    @classmethod
    def parse_score(cls, content: str) -> int | None:
        if not content:
            return None
        match = cls.SCORE_PATTERN.search(content)
        if not match:
            return None
        try:
            score = int(match.group(1))
        except ValueError:
            return None
        return max(0, min(100, score))

    @classmethod
    def parse(cls, content: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "content": content,
            "score": None,
            "summary": "",
            "highlights": [],
            "issues": [],
        }
        data = cls._extract_json(content)
        if isinstance(data, dict) and "score" in data:
            score_raw = data.get("score")
            if isinstance(score_raw, (int, float)):
                result["score"] = max(0, min(100, int(score_raw)))
            result["summary"] = str(data.get("summary") or "")
            highlights = data.get("highlights")
            if isinstance(highlights, list):
                result["highlights"] = [str(h) for h in highlights if h]
            raw_issues = data.get("issues")
            if isinstance(raw_issues, list):
                result["issues"] = [
                    validated
                    for item in raw_issues
                    if (validated := cls._validate_issue(item)) is not None
                ]
            return result
        # Fallback: regex score extraction
        result["score"] = cls.parse_score(content)
        return result


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
        project_id = await self._resolve_project_id(payload)
        exclude_file_types, ignore_patterns = await self._load_project_config(project_id, db)
        filtered_changes, filter_summary = await self._filter_changes(changes, exclude_file_types, ignore_patterns)

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
        max_tokens = self._resolve_max_tokens(provider_config.get("max_tokens"), default=20480)

        context_window_tokens = self._resolve_positive_int(
            provider_config.get("context_window") or provider_config.get("max_context_tokens"),
            default=self._DEFAULT_CONTEXT_WINDOW,
        )
        reserve_tokens = self._resolve_positive_int(
            provider_config.get("prompt_reserve_tokens"),
            default=self._DEFAULT_PROMPT_RESERVE_TOKENS,
        )
        input_safety_ratio = self._resolve_ratio(
            provider_config.get("input_safety_ratio"),
            default=self._DEFAULT_INPUT_SAFETY_RATIO,
        )
        input_budget_tokens = self._compute_input_budget(
            context_window_tokens=context_window_tokens,
            max_tokens=max_tokens,
            reserve_tokens=reserve_tokens,
            input_safety_ratio=input_safety_ratio,
        )

        system_message = self._settings.GPT_MESSAGE
        custom_prompt = payload.get("custom_prompt")
        if isinstance(custom_prompt, str) and custom_prompt.strip():
            system_message = custom_prompt.strip()

        file_units = self._build_file_units(filtered_changes)
        chunk_plan = self._plan_chunks(file_units, input_budget_tokens)

        map_calls: list[dict[str, Any]] = []
        map_outputs: list[dict[str, Any]] = []
        map_duration_total = 0
        map_prompt_tokens_total = 0
        map_completion_tokens_total = 0
        map_reasoning_tokens_total = 0
        map_contents: list[str] = []
        reduce_call: dict[str, Any] | None = None

        if not chunk_plan["chunks"]:
            fallback = self._build_overflow_only_result(chunk_plan["overflow_files"])
            fallback["files_reviewed"] = [item.get("file_path", "") for item in file_units]
            fallback["llm_provider"] = provider.name
            fallback["llm_model"] = str(provider_config.get("model") or provider.name)
            fallback["filter_summary"] = filter_summary
            fallback["llm_trace"] = {
                "request": {
                    "provider": provider.name,
                    "protocol": provider.protocol,
                    "model": str(provider_config.get("model") or ""),
                    "max_tokens": max_tokens,
                    "prompt_length": 0,
                    "prompt_preview": "",
                    "prompt_preview_truncated": False,
                    "system_message_length": len(system_message),
                    "system_message_preview": system_message,
                    "system_message_preview_truncated": False,
                    "chunking_enabled": True,
                    "context_window_tokens": context_window_tokens,
                    "reserve_tokens": reserve_tokens,
                    "input_safety_ratio": input_safety_ratio,
                    "input_budget_tokens": input_budget_tokens,
                    "total_estimated_input_tokens": chunk_plan["total_estimated_tokens"],
                    "estimated_map_request_count": chunk_plan["estimated_map_request_count"],
                    "actual_map_request_count": 0,
                    "reduce_request_count": 0,
                    "total_request_count": 0,
                    "overflow_file_count": len(chunk_plan["overflow_files"]),
                    "overflow_files": json.dumps(chunk_plan["overflow_files"], ensure_ascii=False, indent=2),
                    "chunk_plan": json.dumps(chunk_plan["chunks_meta"], ensure_ascii=False, indent=2),
                    "map_calls": "[]",
                    "reduce_call": "-",
                },
                "response": {
                    "model": str(provider_config.get("model") or provider.name),
                    "duration_ms": 0,
                    "content_length": len(fallback.get("content") or ""),
                    "content_preview": str(fallback.get("content") or ""),
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
            return fallback

        total_chunks = len(chunk_plan["chunks"])
        for idx, chunk in enumerate(chunk_plan["chunks"], start=1):
            chunk_prompt = self._build_chunk_prompt(
                chunk_context=chunk["context"],
                chunk_index=idx,
                chunk_count=total_chunks,
            )
            chunk_max_tokens = self._resolve_chunk_max_tokens(
                chunk_tokens=chunk["estimated_tokens"],
                context_window_tokens=context_window_tokens,
                reserve_tokens=reserve_tokens,
                input_safety_ratio=input_safety_ratio,
                default_max_tokens=max_tokens,
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

            response_trace = self._extract_response_trace(llm_response)
            parsed = await self._parse_review_result(llm_response.content)
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
            fallback = self._build_overflow_only_result(chunk_plan["overflow_files"])
            fallback["files_reviewed"] = [item.get("file_path", "") for item in file_units]
            fallback["llm_provider"] = provider.name
            fallback["llm_model"] = str(provider_config.get("model") or provider.name)
            fallback["filter_summary"] = filter_summary
            fallback["llm_trace"] = {
                "request": {
                    "provider": provider.name,
                    "protocol": provider.protocol,
                    "model": str(provider_config.get("model") or ""),
                    "max_tokens": max_tokens,
                    "prompt_length": 0,
                    "prompt_preview": "",
                    "prompt_preview_truncated": False,
                    "system_message_length": len(system_message),
                    "system_message_preview": system_message,
                    "system_message_preview_truncated": False,
                    "chunking_enabled": True,
                    "context_window_tokens": context_window_tokens,
                    "reserve_tokens": reserve_tokens,
                    "input_safety_ratio": input_safety_ratio,
                    "input_budget_tokens": input_budget_tokens,
                    "total_estimated_input_tokens": chunk_plan["total_estimated_tokens"],
                    "estimated_map_request_count": chunk_plan["estimated_map_request_count"],
                    "actual_map_request_count": 0,
                    "reduce_request_count": 0,
                    "total_request_count": 0,
                    "overflow_file_count": len(chunk_plan["overflow_files"]),
                    "overflow_files": json.dumps(chunk_plan["overflow_files"], ensure_ascii=False, indent=2),
                    "chunk_plan": json.dumps(chunk_plan["chunks_meta"], ensure_ascii=False, indent=2),
                    "map_calls": "[]",
                    "reduce_call": "-",
                },
                "response": {
                    "model": str(provider_config.get("model") or provider.name),
                    "duration_ms": 0,
                    "content_length": len(fallback.get("content") or ""),
                    "content_preview": str(fallback.get("content") or ""),
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
            return fallback

        reduce_required = len(map_outputs) > 1
        final_content = map_contents[0]
        final_parsed = await self._parse_review_result(final_content)
        final_response_trace = map_calls[0]["response"] if map_calls else {}
        llm_model = str(final_response_trace.get("model") or provider_config.get("model") or provider.name)
        reduce_request_count = 0
        reduce_content = ""
        if reduce_required:
            reduce_prompt = self._build_reduce_prompt(map_outputs, chunk_plan["overflow_files"])
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

            reduce_response_trace = self._extract_response_trace(reduce_response)
            reduce_parsed = await self._parse_review_result(reduce_response.content)
            reduce_content = str(reduce_response.content or "")
            reduce_call = {
                "request": {
                    "chunk_index": len(map_calls) + 1,
                    "chunk_count": len(map_calls) + 1,
                    "file_count": 0,
                    "files": [],
                    "estimated_input_tokens": self._estimate_tokens(reduce_prompt),
                    "max_tokens": max_tokens,
                    "prompt_length": len(reduce_prompt),
                    "prompt_preview": reduce_prompt,
                    "prompt_preview_truncated": False,
                    "system_message_length": len(system_message),
                    "system_message_preview": system_message,
                    "system_message_preview_truncated": False,
                },
                "response": reduce_response_trace,
            }
            reduce_request_count = 1
            llm_model = str(reduce_response_trace.get("model") or llm_model)

            if self._is_structured_review_result(reduce_parsed):
                final_content = reduce_content
                final_parsed = reduce_parsed
                final_response_trace = reduce_response_trace
            else:
                merged = self._merge_map_outputs(map_outputs, chunk_plan["overflow_files"])
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
        llm_trace = {
            "request": {
                "provider": provider.name,
                "protocol": provider.protocol,
                "model": str(provider_config.get("model") or ""),
                "max_tokens": max_tokens,
                "prompt_length": len(reduce_call["request"]["prompt_preview"]) if reduce_call else int(map_calls[0]["request"]["prompt_length"]),
                "prompt_preview": reduce_call["request"]["prompt_preview"] if reduce_call else map_calls[0]["request"]["prompt_preview"],
                "prompt_preview_truncated": False,
                "system_message_length": len(system_message),
                "system_message_preview": system_message,
                "system_message_preview_truncated": False,
                "chunking_enabled": total_chunks > 1,
                "context_window_tokens": context_window_tokens,
                "reserve_tokens": reserve_tokens,
                "input_safety_ratio": input_safety_ratio,
                "input_budget_tokens": input_budget_tokens,
                "total_estimated_input_tokens": chunk_plan["total_estimated_tokens"],
                "estimated_map_request_count": chunk_plan["estimated_map_request_count"],
                "actual_map_request_count": len(map_calls),
                "reduce_request_count": reduce_request_count,
                "total_request_count": len(map_calls) + reduce_request_count,
                "overflow_file_count": len(chunk_plan["overflow_files"]),
                "overflow_files": json.dumps(chunk_plan["overflow_files"], ensure_ascii=False, indent=2),
                "chunk_plan": json.dumps(chunk_plan["chunks_meta"], ensure_ascii=False, indent=2),
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
                "map_duration_ms_total": map_duration_total,
                "map_prompt_tokens_total": map_prompt_tokens_total,
                "map_completion_tokens_total": map_completion_tokens_total,
                "map_reasoning_tokens_total": map_reasoning_tokens_total,
                "total_request_count": len(map_calls) + reduce_request_count,
                "map_outputs": json.dumps(map_outputs, ensure_ascii=False, indent=2),
                "reduce_content": reduce_content,
            },
        }

        final_parsed["content"] = str(final_content or "")
        final_parsed["files_reviewed"] = [item.get("file_path", "") for item in file_units]
        final_parsed["llm_provider"] = provider.name
        final_parsed["llm_model"] = llm_model
        final_parsed["filter_summary"] = filter_summary
        final_parsed["llm_trace"] = llm_trace
        final_parsed["overflow_files"] = chunk_plan["overflow_files"]
        return final_parsed

    async def _resolve_project_id(self, payload: dict[str, Any]) -> int | None:
        project_data = payload.get("project")
        if isinstance(project_data, dict):
            value = project_data.get("id")
            if isinstance(value, int):
                return value

        value = payload.get("project_id")
        if isinstance(value, int):
            return value
        return None

    def _resolve_max_tokens(self, value: Any, default: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        if parsed <= 0:
            return default
        return parsed

    def _resolve_positive_int(self, value: Any, default: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        return parsed if parsed > 0 else default

    def _resolve_ratio(self, value: Any, default: float) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            parsed = default
        if parsed <= 0.1:
            return default
        if parsed >= 0.95:
            return 0.95
        return parsed

    def _compute_input_budget(
        self,
        context_window_tokens: int,
        max_tokens: int,
        reserve_tokens: int,
        input_safety_ratio: float,
    ) -> int:
        remaining = max(context_window_tokens - max_tokens - reserve_tokens, 0)
        return max(int(math.floor(remaining * input_safety_ratio)), 1)

    async def _load_project_config(
        self,
        project_id: int | None,
        db: AsyncSession,
    ) -> tuple[list[str], list[str]]:
        default_exclude = list(self._settings.EXCLUDE_FILE_TYPES)
        default_ignore = list(self._settings.IGNORE_FILE_TYPES)
        if project_id is None:
            return default_exclude, default_ignore

        stmt = select(Project).where(Project.project_id == project_id).limit(1)
        project = (await db.execute(stmt)).scalars().first()
        if project is None:
            return default_exclude, default_ignore

        exclude_file_types = (
            default_exclude
            if project.exclude_file_types is None
            else list(project.exclude_file_types)
        )
        ignore_patterns = (
            default_ignore
            if project.ignore_file_patterns is None
            else list(project.ignore_file_patterns)
        )
        return exclude_file_types, ignore_patterns

    async def _filter_changes(
        self,
        changes: list[dict[str, Any]],
        exclude_file_types: list[str],
        ignore_patterns: list[str],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        deleted_file_count = 0
        renamed_without_diff_count = 0
        excluded_by_type_count = 0
        ignored_by_pattern_count = 0
        excluded_by_type_sample: list[str] = []
        ignored_by_pattern_sample: list[str] = []
        for change in changes:
            if change.get("deleted_file"):
                deleted_file_count += 1
                continue
            if change.get("renamed_file") and not change.get("diff"):
                renamed_without_diff_count += 1
                continue

            file_path = str(change.get("new_path") or change.get("old_path") or "")
            if not file_path:
                continue

            matched_type = await self._matched_excluded_type(file_path, exclude_file_types)
            if matched_type is not None:
                excluded_by_type_count += 1
                if len(excluded_by_type_sample) < 5:
                    excluded_by_type_sample.append(file_path)
                continue
            matched_pattern = await self._matched_ignore_pattern(file_path, ignore_patterns)
            if matched_pattern is not None:
                ignored_by_pattern_count += 1
                if len(ignored_by_pattern_sample) < 5:
                    ignored_by_pattern_sample.append(file_path)
                continue

            filtered.append(change)
        raw_file_count = len(changes)
        filtered_file_count = len(filtered)
        summary = {
            "raw_file_count": raw_file_count,
            "filtered_file_count": filtered_file_count,
            "removed_file_count": raw_file_count - filtered_file_count,
            "excluded_by_type_count": excluded_by_type_count,
            "ignored_by_pattern_count": ignored_by_pattern_count,
            "deleted_file_count": deleted_file_count,
            "renamed_without_diff_count": renamed_without_diff_count,
            "excluded_by_type_sample": excluded_by_type_sample,
            "ignored_by_pattern_sample": ignored_by_pattern_sample,
        }
        return filtered, summary

    async def _matched_excluded_type(
        self,
        file_path: str,
        exclude_file_types: list[str],
    ) -> str | None:
        normalized_path = file_path.lower()
        for file_type in exclude_file_types:
            suffix = str(file_type).strip().lower()
            if suffix and normalized_path.endswith(suffix):
                return suffix
        return None

    async def _matched_ignore_pattern(
        self,
        file_path: str,
        ignore_patterns: list[str],
    ) -> str | None:
        normalized_path = file_path.strip()
        for pattern in ignore_patterns:
            item = str(pattern).strip()
            if not item:
                continue
            if item in normalized_path:
                return item
            if fnmatch.fnmatch(normalized_path, item):
                return item
        return None

    def _estimate_tokens(self, text: str) -> int:
        if not text:
            return 0
        return max(1, math.ceil(len(text) / self._TOKEN_ESTIMATE_DIVISOR))

    def _build_file_units(self, changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        units: list[dict[str, Any]] = []
        for change in changes:
            file_path = str(change.get("new_path") or change.get("old_path") or "unknown")
            diff = str(change.get("diff") or "")
            context = f"## 文件: {file_path}\n\n```diff\n{diff}\n```\n"
            units.append(
                {
                    "file_path": file_path,
                    "context": context,
                    "estimated_tokens": self._estimate_tokens(context),
                }
            )
        return units

    def _plan_chunks(self, file_units: list[dict[str, Any]], input_budget_tokens: int) -> dict[str, Any]:
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
                token_est = self._estimate_tokens(context)
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

    def _resolve_chunk_max_tokens(
        self,
        chunk_tokens: int,
        context_window_tokens: int,
        reserve_tokens: int,
        input_safety_ratio: float,
        default_max_tokens: int,
    ) -> int:
        if chunk_tokens <= 0:
            return default_max_tokens

        base_budget = self._compute_input_budget(
            context_window_tokens=context_window_tokens,
            max_tokens=default_max_tokens,
            reserve_tokens=reserve_tokens,
            input_safety_ratio=input_safety_ratio,
        )
        if chunk_tokens <= base_budget:
            return default_max_tokens

        required_input_room = int(math.ceil(chunk_tokens / max(input_safety_ratio, 0.1)))
        candidate = context_window_tokens - reserve_tokens - required_input_room
        if candidate < self._MIN_MAX_TOKENS:
            return 0
        return min(default_max_tokens, candidate)

    def _build_chunk_prompt(self, chunk_context: str, chunk_index: int, chunk_count: int) -> str:
        return (
            f"你正在审查一个超大 MR 的分片 {chunk_index}/{chunk_count}。\n"
            "注意：文件不可拆分，本次请求只包含其中一部分完整文件。\n"
            "请仅根据当前分片中的代码变更给出严格审查结论，并按照约定 JSON 返回。\n\n"
            f"{chunk_context}"
        )

    def _build_reduce_prompt(self, map_outputs: list[dict[str, Any]], overflow_files: list[str]) -> str:
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

    def _extract_response_trace(self, llm_response: LLMResponse) -> dict[str, Any]:
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

    def _is_structured_review_result(self, parsed: dict[str, Any]) -> bool:
        if not isinstance(parsed, dict):
            return False
        has_summary = bool(str(parsed.get("summary") or "").strip())
        issues = parsed.get("issues")
        has_issues = isinstance(issues, list) and len(issues) > 0
        highlights = parsed.get("highlights")
        has_highlights = isinstance(highlights, list) and len(highlights) > 0
        has_score = isinstance(parsed.get("score"), int)
        return has_summary or has_issues or has_highlights or has_score

    def _merge_map_outputs(self, map_outputs: list[dict[str, Any]], overflow_files: list[str]) -> dict[str, Any]:
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
                if len(highlights) >= self._MAX_HIGHLIGHTS_IN_FALLBACK:
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
                if len(issues) >= self._MAX_ISSUES_IN_FALLBACK:
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

    def _build_overflow_only_result(self, overflow_files: list[str]) -> dict[str, Any]:
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

    async def _parse_review_result(self, content: str) -> dict[str, Any]:
        return ReviewResultParser.parse(content)
