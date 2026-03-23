from __future__ import annotations

import asyncio
import json
import os
import shutil
from time import perf_counter
from typing import Any

from app.llm.base import ProtocolAdapter
from app.llm.types import LLMProtocol, LLMRequest, LLMResponse


class ClaudeCliAdapter(ProtocolAdapter):
    @classmethod
    def protocol(cls) -> LLMProtocol:
        return LLMProtocol.claude_cli

    async def validate(self, config: dict[str, Any]) -> tuple[bool, str | None]:
        cli_path = str(config.get("cli_path") or "claude").strip()
        if not cli_path:
            return False, "Missing 'cli_path' in provider config."
        if os.path.sep not in cli_path and shutil.which(cli_path) is None:
            return False, f"CLI executable not found in PATH: {cli_path}"
        timeout = int(config.get("timeout", 300))
        if timeout <= 0:
            return False, "'timeout' must be > 0."
        return True, None

    async def review(self, request: LLMRequest, config: dict[str, Any]) -> LLMResponse:
        ok, err = await self.validate(config)
        if not ok:
            raise ValueError(err)

        cli_path = str(config.get("cli_path") or "claude")
        timeout = int(config.get("timeout", 300))

        prompt = request.prompt
        if request.system_message:
            prompt = f"{request.system_message}\n\n{request.prompt}"

        # v1 uses: claude -p <prompt> --output-format json
        command = [cli_path, "-p", prompt, "--output-format", "json"]

        env = os.environ.copy()
        base_url = config.get("anthropic_base_url")
        auth_token = config.get("anthropic_auth_token")
        if base_url:
            env["ANTHROPIC_BASE_URL"] = str(base_url)
        if auth_token:
            env["ANTHROPIC_AUTH_TOKEN"] = str(auth_token)

        cwd = request.repo_path or None
        started = perf_counter()

        process = await asyncio.create_subprocess_exec(
            *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            env=env, cwd=cwd,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            raise TimeoutError(f"Claude CLI timed out after {timeout}s.")

        duration_ms = int((perf_counter() - started) * 1000)
        stderr_text = stderr.decode("utf-8", errors="replace").strip()

        if process.returncode != 0:
            raise RuntimeError(f"Claude CLI exit code {process.returncode}: {stderr_text}")

        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        content = stdout_text
        model = "claude-cli"
        raw_response: dict[str, Any] | None = None

        if stdout_text:
            try:
                parsed = json.loads(stdout_text)
            except json.JSONDecodeError:
                parsed = None

            if isinstance(parsed, dict):
                raw_response = parsed
                model = str(parsed.get("model") or model)
                # Claude CLI JSON: result field or content array
                node = parsed.get("result") or parsed.get("content") or parsed.get("text") or parsed.get("response")
                if isinstance(node, list):
                    parts = []
                    for item in node:
                        if isinstance(item, dict) and "text" in item:
                            parts.append(str(item["text"]))
                        elif item is not None:
                            parts.append(str(item))
                    content = "\n".join(parts).strip()
                elif node is not None:
                    content = str(node)

        if raw_response is None:
            raw_response = {"stdout": stdout_text, "stderr": stderr_text}

        return LLMResponse(
            content=content, model=model, usage=None,
            duration_ms=duration_ms, raw_response=raw_response,
        )
