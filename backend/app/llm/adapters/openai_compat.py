from __future__ import annotations

from time import perf_counter
from typing import Any

import httpx

from app.llm.base import ProtocolAdapter
from app.llm.types import LLMProtocol, LLMRequest, LLMResponse


class OpenAICompatAdapter(ProtocolAdapter):
    @classmethod
    def protocol(cls) -> LLMProtocol:
        return LLMProtocol.openai_compatible

    async def validate(self, config: dict[str, Any]) -> tuple[bool, str | None]:
        if not str(config.get("api_base") or "").strip():
            return False, "Missing 'api_base' in provider config."
        if not str(config.get("model") or "").strip():
            return False, "Missing 'model' in provider config."
        return True, None

    async def review(self, request: LLMRequest, config: dict[str, Any]) -> LLMResponse:
        ok, err = await self.validate(config)
        if not ok:
            raise ValueError(err)

        api_base = str(config["api_base"]).rstrip("/")
        model = str(config["model"])
        api_key = str(config.get("api_key") or "")
        timeout = float(config.get("timeout", 300))
        initial_max_tokens = self._resolve_initial_max_tokens(request.max_tokens, config)
        request_mode = self._resolve_request_mode(model, config)
        endpoint_path = "/responses" if request_mode == "responses" else "/chat/completions"

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        request_payload, token_field = self._build_request_payload(
            mode=request_mode,
            model=model,
            request=request,
            initial_max_tokens=initial_max_tokens,
        )

        started = perf_counter()
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{api_base}{endpoint_path}", headers=headers, json=request_payload)
            resp.raise_for_status()
            body = resp.json()

            content = self._extract_content(body)
            if not content and self._should_retry_empty_length_response(body):
                retry_max_tokens = self._resolve_retry_max_tokens(request.max_tokens, config)
                current_max_tokens = self._safe_int(request_payload.get(token_field))
                if current_max_tokens <= 0:
                    current_max_tokens = request.max_tokens
                if retry_max_tokens > current_max_tokens:
                    retry_payload = dict(request_payload)
                    retry_payload[token_field] = retry_max_tokens
                    retry_resp = await client.post(
                        f"{api_base}{endpoint_path}",
                        headers=headers,
                        json=retry_payload,
                    )
                    retry_resp.raise_for_status()
                    retry_body = retry_resp.json()
                    retry_content = self._extract_content(retry_body)
                    if retry_content:
                        body = retry_body
                        content = retry_content
                    elif isinstance(retry_body, dict):
                        body = retry_body

        duration_ms = int((perf_counter() - started) * 1000)

        if not content:
            content = self._extract_content(body)
        usage = body.get("usage") if isinstance(body, dict) else None

        return LLMResponse(
            content=content,
            model=str(body.get("model", model)) if isinstance(body, dict) else model,
            usage=usage if isinstance(usage, dict) else None,
            duration_ms=duration_ms,
            raw_response=body if isinstance(body, dict) else {"raw": body},
        )

    def _resolve_request_mode(self, model: str, config: dict[str, Any]) -> str:
        configured = str(
            config.get("request_mode")
            or config.get("api_style")
            or config.get("api_mode")
            or ""
        ).strip().lower()
        if configured in ("responses", "response"):
            return "responses"
        if configured in ("chat", "chat_completions", "chat-completions"):
            return "chat_completions"
        if "codex" in model.lower():
            return "responses"
        return "chat_completions"

    def _build_request_payload(
        self,
        mode: str,
        model: str,
        request: LLMRequest,
        initial_max_tokens: int,
    ) -> tuple[dict[str, Any], str]:
        if mode == "responses":
            input_items: list[dict[str, str]] = []
            if request.system_message:
                input_items.append({"role": "system", "content": request.system_message})
            input_items.append({"role": "user", "content": request.prompt})
            return {
                "model": model,
                "input": input_items,
                "temperature": request.temperature,
                "max_output_tokens": initial_max_tokens,
            }, "max_output_tokens"

        messages: list[dict[str, str]] = []
        if request.system_message:
            messages.append({"role": "system", "content": request.system_message})
        messages.append({"role": "user", "content": request.prompt})
        return {
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": initial_max_tokens,
        }, "max_tokens"

    def _resolve_retry_max_tokens(self, current_max_tokens: int, config: dict[str, Any]) -> int:
        try:
            configured = int(config.get("retry_max_tokens", 0))
        except (TypeError, ValueError):
            configured = 0
        if configured > current_max_tokens:
            return configured
        doubled = max(current_max_tokens * 2, 8192)
        return min(doubled, 65536)

    def _resolve_initial_max_tokens(self, request_max_tokens: int, config: dict[str, Any]) -> int:
        try:
            configured = int(config.get("max_tokens", 0))
        except (TypeError, ValueError):
            configured = 0
        if configured > 0:
            return configured
        return request_max_tokens

    def _should_retry_empty_length_response(self, body: Any) -> bool:
        if self._should_retry_openai_responses_empty_length(body):
            return True

        if not isinstance(body, dict):
            return False
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices:
            return False
        first = choices[0]
        if not isinstance(first, dict):
            return False
        if str(first.get("finish_reason") or "") != "length":
            return False
        message = first.get("message")
        message_dict = message if isinstance(message, dict) else {}
        if self._extract_text_node(message_dict.get("content")).strip():
            return False

        usage = body.get("usage")
        usage_dict = usage if isinstance(usage, dict) else {}
        completion_tokens = self._safe_int(usage_dict.get("completion_tokens"))
        details = usage_dict.get("completion_tokens_details")
        details_dict = details if isinstance(details, dict) else {}
        reasoning_tokens = self._safe_int(details_dict.get("reasoning_tokens"))

        if completion_tokens <= 0:
            return True
        if reasoning_tokens >= completion_tokens:
            return True
        return False

    def _should_retry_openai_responses_empty_length(self, body: Any) -> bool:
        if not isinstance(body, dict):
            return False
        if self._extract_responses_text(body).strip():
            return False

        reason = ""
        details_raw = body.get("incomplete_details")
        if isinstance(details_raw, dict):
            reason = str(details_raw.get("reason") or "").lower()
        finish_reason = str(body.get("finish_reason") or "").lower()
        if reason not in ("max_output_tokens", "length") and finish_reason != "length":
            return False

        usage_raw = body.get("usage")
        usage = usage_raw if isinstance(usage_raw, dict) else {}
        output_tokens = self._safe_int(usage.get("output_tokens") or usage.get("completion_tokens"))
        output_details_raw = usage.get("output_tokens_details") or usage.get("completion_tokens_details")
        output_details = output_details_raw if isinstance(output_details_raw, dict) else {}
        reasoning_tokens = self._safe_int(output_details.get("reasoning_tokens"))
        if output_tokens <= 0:
            return True
        if reasoning_tokens >= output_tokens:
            return True
        return True

    def _extract_content(self, body: Any) -> str:
        if not isinstance(body, dict):
            return str(body)

        # Prefer OpenAI Responses/Codex-style extraction:
        # only assistant output text should be returned; reasoning/tool blocks are ignored.
        responses_text = self._extract_responses_text(body)
        if responses_text:
            return responses_text

        choices = body.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            text = self._extract_text_node(first)
            if text:
                return text

        # Compatible with providers that return the OpenAI Responses-style payload
        # under `output`/`output_text` while still using an OpenAI-compatible endpoint.
        for key in (
            "output_text",
            "output",
            "content",
            "text",
            "response",
            "message",
            "result",
            "answer",
            "generated_text",
            "completion",
            "data",
        ):
            text = self._extract_text_node(body.get(key))
            if text:
                return text

        return ""

    def _extract_responses_text(self, body: Any) -> str:
        if not isinstance(body, dict):
            return ""

        direct_output_text = self._extract_text_node(body.get("output_text")).strip()
        if direct_output_text:
            return direct_output_text

        output_text = self._extract_responses_output_text(body.get("output")).strip()
        if output_text:
            return output_text

        nested_response = body.get("response")
        if isinstance(nested_response, dict):
            nested_text = self._extract_responses_text(nested_response).strip()
            if nested_text:
                return nested_text

        return ""

    def _extract_responses_output_text(self, output: Any) -> str:
        if isinstance(output, str):
            return output.strip()

        if isinstance(output, dict):
            output = [output]
        if not isinstance(output, list):
            return ""

        parts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type") or "").lower()

            if item_type == "message" or "content" in item:
                text = self._extract_responses_message_content_text(item.get("content")).strip()
                if text:
                    parts.append(text)
                continue

            if item_type in ("output_text", "text"):
                text = self._extract_text_node(item.get("text") or item.get("content") or item.get("value")).strip()
                if text:
                    parts.append(text)

        return "\n".join(part for part in parts if part).strip()

    def _extract_responses_message_content_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, dict):
            content = [content]
        if not isinstance(content, list):
            return ""

        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    parts.append(text)
                continue
            if not isinstance(item, dict):
                continue
            item_type = str(item.get("type") or "").lower()
            if item_type not in ("output_text", "text", "input_text"):
                continue
            text = self._extract_text_node(item.get("text") or item.get("content") or item.get("value")).strip()
            if text:
                parts.append(text)

        return "\n".join(part for part in parts if part).strip()

    def _safe_int(self, value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    def _extract_text_node(self, node: Any) -> str:
        if node is None:
            return ""
        if isinstance(node, str):
            return node
        if isinstance(node, (int, float, bool)):
            return str(node)
        if isinstance(node, list):
            parts = [self._extract_text_node(item) for item in node]
            return "\n".join([part for part in parts if part])
        if not isinstance(node, dict):
            return str(node)

        # Typical chat-completions shape
        message = node.get("message")
        if message is not None:
            text = self._extract_text_node(message)
            if text:
                return text

        # Common OpenAI-compatible fields (ordered by preference)
        for key in (
            "content",
            "text",
            "output_text",
            "reasoning_content",
            "reasoning",
            "result",
            "answer",
            "generated_text",
            "completion",
            "refusal",
            "arguments",
            "value",
        ):
            text = self._extract_text_node(node.get(key))
            if text:
                return text

        # Fallback for tool/function call objects
        for key in ("tool_calls", "function_call", "function", "delta", "output"):
            text = self._extract_text_node(node.get(key))
            if text:
                return text

        return ""
