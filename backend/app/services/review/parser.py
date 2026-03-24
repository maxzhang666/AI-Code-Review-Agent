from __future__ import annotations

import json
import re
from typing import Any


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
        if severity not in ("critical", "high", "medium", "low"):
            severity = "medium"
        line = item.get("line")
        line_start = item.get("line_start")
        line_end = item.get("line_end")
        if not isinstance(line_start, int):
            line_start = line if isinstance(line, int) else None
        if not isinstance(line_end, int):
            line_end = line_start
        confidence_raw = item.get("confidence")
        confidence = confidence_raw if isinstance(confidence_raw, (int, float)) else None
        if confidence is not None:
            confidence = float(max(0.0, min(1.0, confidence)))
        owner_name_raw = item.get("owner_name")
        owner_email_raw = item.get("owner_email")
        owner_raw = item.get("owner")
        owner_name = str(owner_name_raw).strip() if owner_name_raw is not None else ""
        owner_email = str(owner_email_raw).strip() if owner_email_raw is not None else ""
        owner = str(owner_raw).strip() if owner_raw is not None else ""
        if not owner_name and not owner_email and owner:
            if "@" in owner:
                owner_email = owner
            else:
                owner_name = owner
        file_path = str(item.get("file_path") or item.get("file") or "")
        message = str(item.get("message") or item.get("description") or "")
        code_snippet = str(
            item.get("code_snippet")
            or item.get("problematic_code")
            or item.get("problem_code")
            or item.get("code")
            or item.get("snippet")
            or ""
        )
        return {
            "severity": severity,
            "category": str(item.get("category") or "质量"),
            "subcategory": str(item.get("subcategory") or ""),
            "file": file_path,
            "file_path": file_path,
            "line": line_start,
            "line_start": line_start,
            "line_end": line_end,
            "description": message,
            "message": message,
            "suggestion": str(item.get("suggestion") or ""),
            "code_snippet": code_snippet,
            "problematic_code": code_snippet,
            "owner_name": owner_name or None,
            "owner_email": owner_email or None,
            "owner": owner_name or owner_email or None,
            "confidence": confidence,
            "is_blocking": bool(item.get("is_blocking", False)),
            "is_false_positive": bool(item.get("is_false_positive", False)),
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
