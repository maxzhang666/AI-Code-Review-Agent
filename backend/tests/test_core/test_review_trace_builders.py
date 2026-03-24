from __future__ import annotations

import json

from app.services.review.tracing import (
    build_empty_llm_trace,
    build_final_llm_trace,
)


def test_build_empty_llm_trace_contains_policy_and_conflict_flags() -> None:
    trace = build_empty_llm_trace(
        provider_name="stub-provider",
        provider_protocol="openai_compatible",
        provider_model="stub-model",
        max_tokens=2048,
        system_message="sys",
        prompt_policy="strategy_override_allowed_schema_locked",
        conflict_detected=True,
        context_window_tokens=128000,
        reserve_tokens=3000,
        input_safety_ratio=0.75,
        input_budget_tokens=91964,
        total_estimated_input_tokens=0,
        estimated_map_request_count=0,
        overflow_files=["src/Huge.java"],
        chunk_plan=[],
        response_model="stub-model",
        response_content="fallback",
    )

    request = trace["request"]
    response = trace["response"]
    assert request["prompt_policy"] == "strategy_override_allowed_schema_locked"
    assert request["conflict_detected"] is True
    assert request["map_calls"] == "[]"
    assert request["reduce_call"] == "-"
    assert json.loads(request["overflow_files"]) == ["src/Huge.java"]
    assert json.loads(request["chunk_plan"]) == []
    assert response["content_preview"] == "fallback"


def test_build_final_llm_trace_includes_map_and_reduce_payloads() -> None:
    map_calls = [{"request": {"chunk_index": 1}, "response": {"model": "m"}}]
    map_outputs = [{"chunk_index": 1, "summary": "ok"}]
    reduce_call = {"request": {"chunk_index": 2}, "response": {"model": "m2"}}
    final_response_trace = {
        "content_from_raw_fallback": False,
        "raw_response_length": 0,
        "raw_response_preview": "",
        "finish_reason": "stop",
        "prompt_tokens": 11,
        "completion_tokens": 22,
        "reasoning_tokens": 0,
    }
    trace = build_final_llm_trace(
        provider_name="stub-provider",
        provider_protocol="openai_compatible",
        provider_model="stub-model",
        max_tokens=2048,
        prompt_preview="reduce prompt",
        system_message="sys",
        prompt_policy="strategy_override_allowed_schema_locked",
        conflict_detected=False,
        chunking_enabled=True,
        context_window_tokens=128000,
        reserve_tokens=3000,
        input_safety_ratio=0.75,
        input_budget_tokens=91964,
        total_estimated_input_tokens=123,
        estimated_map_request_count=1,
        actual_map_request_count=1,
        reduce_request_count=1,
        overflow_files=[],
        chunk_plan=[{"chunk_index": 1}],
        map_calls=map_calls,
        reduce_call=reduce_call,
        llm_model="stub-model",
        total_duration_ms=12,
        final_content='{"score": 90}',
        response_content_preview='{"score": 90}',
        final_response_trace=final_response_trace,
        map_duration_ms_total=5,
        map_prompt_tokens_total=6,
        map_completion_tokens_total=7,
        map_reasoning_tokens_total=0,
        map_outputs=map_outputs,
        reduce_content='{"score": 90}',
    )

    request = trace["request"]
    response = trace["response"]
    assert request["prompt_policy"] == "strategy_override_allowed_schema_locked"
    assert request["conflict_detected"] is False
    assert request["reduce_request_count"] == 1
    assert request["total_request_count"] == 2
    assert json.loads(request["map_calls"]) == map_calls
    assert json.loads(request["reduce_call"]) == reduce_call
    assert response["total_request_count"] == 2
    assert response["finish_reason"] == "stop"
