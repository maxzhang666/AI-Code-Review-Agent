from __future__ import annotations

from app.llm.types import LLMRequest
from app.llm.adapters.openai_compat import OpenAICompatAdapter


def test_extract_content_supports_message_content_dict() -> None:
    adapter = OpenAICompatAdapter()
    body = {
        "choices": [
            {
                "message": {
                    "content": {
                        "type": "text",
                        "text": "full review content",
                    }
                }
            }
        ]
    }

    assert adapter._extract_content(body) == "full review content"


def test_extract_content_falls_back_to_reasoning_content() -> None:
    adapter = OpenAICompatAdapter()
    body = {
        "choices": [
            {
                "message": {
                    "content": "",
                    "reasoning_content": "long reasoning review content",
                }
            }
        ]
    }

    assert adapter._extract_content(body) == "long reasoning review content"


def test_extract_content_supports_output_api_shape() -> None:
    adapter = OpenAICompatAdapter()
    body = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "review result from output api",
                    }
                ],
            }
        ]
    }

    assert adapter._extract_content(body) == "review result from output api"


def test_extract_content_supports_result_field() -> None:
    adapter = OpenAICompatAdapter()
    body = {
        "result": "review result from result field",
    }

    assert adapter._extract_content(body) == "review result from result field"


def test_extract_content_supports_codex_responses_output_and_ignores_reasoning() -> None:
    adapter = OpenAICompatAdapter()
    body = {
        "id": "resp_123",
        "object": "response",
        "output": [
            {
                "type": "reasoning",
                "summary": [{"type": "summary_text", "text": "internal reasoning"}],
            },
            {
                "type": "message",
                "role": "assistant",
                "content": [
                    {"type": "output_text", "text": '{"score": 93, "summary": "ok"}'},
                ],
            },
        ],
    }

    assert adapter._extract_content(body) == '{"score": 93, "summary": "ok"}'


def test_extract_content_supports_nested_response_wrapper() -> None:
    adapter = OpenAICompatAdapter()
    body = {
        "response": {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "nested response output"}],
                }
            ]
        }
    }

    assert adapter._extract_content(body) == "nested response output"


def test_should_retry_when_reasoning_exhausts_completion_budget() -> None:
    adapter = OpenAICompatAdapter()
    body = {
        "choices": [
            {
                "message": {"content": ""},
                "finish_reason": "length",
            }
        ],
        "usage": {
            "completion_tokens": 4096,
            "completion_tokens_details": {"reasoning_tokens": 4096},
        },
    }

    assert adapter._should_retry_empty_length_response(body) is True


def test_should_not_retry_when_content_exists() -> None:
    adapter = OpenAICompatAdapter()
    body = {
        "choices": [
            {
                "message": {"content": "ok"},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "completion_tokens": 100,
            "completion_tokens_details": {"reasoning_tokens": 10},
        },
    }

    assert adapter._should_retry_empty_length_response(body) is False


def test_should_retry_when_codex_response_hits_max_output_tokens_with_empty_output() -> None:
    adapter = OpenAICompatAdapter()
    body = {
        "status": "incomplete",
        "incomplete_details": {"reason": "max_output_tokens"},
        "output": [{"type": "reasoning", "summary": [{"type": "summary_text", "text": "thinking"}]}],
        "usage": {
            "output_tokens": 4096,
            "output_tokens_details": {"reasoning_tokens": 4096},
        },
    }

    assert adapter._should_retry_empty_length_response(body) is True


def test_should_not_retry_when_codex_response_has_message_output() -> None:
    adapter = OpenAICompatAdapter()
    body = {
        "status": "incomplete",
        "incomplete_details": {"reason": "max_output_tokens"},
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": '{"score": 90}'}],
            }
        ],
        "usage": {
            "output_tokens": 4096,
            "output_tokens_details": {"reasoning_tokens": 3500},
        },
    }

    assert adapter._should_retry_empty_length_response(body) is False


def test_resolve_initial_max_tokens_prefers_config_value() -> None:
    adapter = OpenAICompatAdapter()
    assert adapter._resolve_initial_max_tokens(4096, {"max_tokens": 8192}) == 8192


def test_resolve_initial_max_tokens_falls_back_to_request_value() -> None:
    adapter = OpenAICompatAdapter()
    assert adapter._resolve_initial_max_tokens(4096, {"max_tokens": "invalid"}) == 4096


def test_resolve_request_mode_uses_responses_for_codex_by_default() -> None:
    adapter = OpenAICompatAdapter()
    assert adapter._resolve_request_mode("codex-mini-latest", {}) == "responses"


def test_resolve_request_mode_can_be_forced_to_chat() -> None:
    adapter = OpenAICompatAdapter()
    assert adapter._resolve_request_mode("codex-mini-latest", {"request_mode": "chat_completions"}) == "chat_completions"


def test_build_request_payload_for_responses_mode() -> None:
    adapter = OpenAICompatAdapter()
    request = LLMRequest(prompt="review", system_message="sys", max_tokens=2048)
    payload, token_field = adapter._build_request_payload(
        mode="responses",
        model="codex-mini-latest",
        request=request,
        initial_max_tokens=2048,
    )

    assert token_field == "max_output_tokens"
    assert payload.get("model") == "codex-mini-latest"
    assert payload.get("max_output_tokens") == 2048
    input_items = payload.get("input")
    assert isinstance(input_items, list)
    assert input_items[0]["role"] == "system"
    assert input_items[1]["role"] == "user"
