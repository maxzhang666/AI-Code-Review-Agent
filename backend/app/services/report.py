from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.config import get_settings
from app.core.logging import get_logger


class ReportGenerator:
    def __init__(self, request_id: str | None = None) -> None:
        self._request_id = request_id
        self._settings = get_settings()
        self._logger = get_logger(__name__, request_id)
        self._tz = ZoneInfo(self._settings.TIMEZONE)

    async def generate_mock(self, mr_info: dict[str, Any]) -> dict[str, Any]:
        try:
            now = await self._format_now()
            project_name = str(mr_info.get("project_name") or "未知项目")
            mr_title = str(mr_info.get("title") or "未知MR")
            author = str(mr_info.get("author") or "未知作者")
            file_count = int(mr_info.get("file_count") or 0)
            changes_count = int(mr_info.get("changes_count") or 0)

            content = (
                "### 😀代码评分:85\n\n"
                "#### ✅代码优点:\n"
                "- 代码结构清晰，业务逻辑可读性良好。\n\n"
                "#### 🤔问题点:\n"
                "- 部分错误处理路径可以进一步细化。\n\n"
                "#### 🎯修改建议:\n"
                "- 为外部调用增加更多上下文日志与降级策略。\n\n"
                "#### 💻修改后的代码:\n"
                "```python\n"
                "# mock placeholder\n"
                "```"
            )

            wrapped = (
                f"# 🤖 代码审查报告 (Mock模式)\n\n"
                f"- 项目: {project_name}\n"
                f"- MR: {mr_title}\n"
                f"- 作者: {author}\n"
                f"- 时间: {now}\n"
                f"- 文件数: {file_count}\n"
                f"- 变更行数: {changes_count}\n\n"
                f"{content}\n"
            )

            return {
                "content": wrapped,
                "metadata": {
                    "is_mock": True,
                    "generated_at": datetime.now(self._tz).isoformat(),
                    "score": 85,
                    "issues_found": 1,
                    "project_name": project_name,
                    "mr_title": mr_title,
                    "file_count": file_count,
                    "changes_count": changes_count,
                },
            }
        except Exception as exc:
            self._logger.log_error_with_context("report_generate_mock_failed", error=exc)
            return await self._generate_error_report("Mock report generation failed", str(exc))

    async def generate(
        self,
        llm_text: str,
        mr_info: dict[str, Any],
        llm_model: str,
    ) -> dict[str, Any]:
        try:
            now = await self._format_now()
            project_name = str(mr_info.get("project_name") or "未知项目")
            mr_title = str(mr_info.get("title") or "未知MR")
            author = str(mr_info.get("author") or "未知作者")
            file_count = int(mr_info.get("file_count") or 0)
            changes_count = int(mr_info.get("changes_count") or 0)

            issues = mr_info.get("issues", [])
            summary = mr_info.get("summary", "")
            highlights = mr_info.get("highlights", [])

            if isinstance(issues, list) and (issues or summary):
                score = mr_info.get("score")
                if not isinstance(score, (int, float)):
                    score = await self._extract_score(llm_text)
                issues_count = len(issues)

                severity_map = {"high": "🔴", "medium": "🟡", "low": "🟢"}

                body_parts = [
                    "# 🤖 AI代码审查报告\n",
                    f"- 项目: {project_name}",
                    f"- MR: {mr_title}",
                    f"- 作者: {author}",
                    f"- 时间: {now}",
                    f"- 模型: {llm_model}",
                    f"- 文件数: {file_count}",
                    f"- 变更行数: {changes_count}",
                    f"- 评分: {int(score)}/100\n",
                    "---\n",
                    f"## 📝 审查摘要\n\n{summary}\n",
                ]

                if isinstance(highlights, list) and highlights:
                    body_parts.append("## ✅ 代码优点\n")
                    for h in highlights:
                        body_parts.append(f"- {h}")
                    body_parts.append("")

                if issues:
                    body_parts.append(f"## 🤔 问题列表 ({issues_count}个)\n")
                    for idx, issue in enumerate(issues, 1):
                        sev = str(issue.get("severity", "medium"))
                        icon = severity_map.get(sev, "🟡")
                        cat = issue.get("category", "")
                        file_path = issue.get("file", "")
                        line = issue.get("line")
                        desc = issue.get("description", "")
                        suggestion = issue.get("suggestion", "")

                        location = file_path
                        if line is not None:
                            location = f"{file_path}:{line}"

                        body_parts.append(f"### {icon} 问题{idx} [{cat}] {location}\n")
                        body_parts.append(f"{desc}\n")
                        if suggestion:
                            body_parts.append(f"**建议:** {suggestion}\n")

                body_parts.append("---\n")
                content = "\n".join(body_parts)
            else:
                score = await self._extract_score(llm_text)
                issues_count = await self._count_issues(llm_text)

                content = (
                    "# 🤖 AI代码审查报告\n\n"
                    f"- 项目: {project_name}\n"
                    f"- MR: {mr_title}\n"
                    f"- 作者: {author}\n"
                    f"- 时间: {now}\n"
                    f"- 模型: {llm_model}\n"
                    f"- 文件数: {file_count}\n"
                    f"- 变更行数: {changes_count}\n\n"
                    "---\n\n"
                    f"{llm_text}\n\n"
                    "---\n"
                )

            return {
                "content": content,
                "metadata": {
                    "is_mock": False,
                    "generated_at": datetime.now(self._tz).isoformat(),
                    "llm_model": llm_model,
                    "score": score,
                    "issues_found": issues_count if not (isinstance(issues, list) and issues) else len(issues),
                    "project_name": project_name,
                    "mr_title": mr_title,
                    "file_count": file_count,
                    "changes_count": changes_count,
                    "original_length": len(llm_text),
                },
            }
        except Exception as exc:
            self._logger.log_error_with_context("report_generate_failed", error=exc)
            return await self._generate_error_report("Report generation failed", str(exc))

    async def _extract_score(self, text: str) -> float:
        patterns = [
            r"代码评分[:：\s]*(\d+(?:\.\d+)?)",
            r"评分[:：\s]*(\d+(?:\.\d+)?)",
            r"得分[:：\s]*(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*/\s*100",
            r"(\d+)分",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            if not matches:
                continue
            try:
                value = float(matches[0])
            except ValueError:
                continue
            if value <= 10:
                value *= 10
            return max(0.0, min(100.0, value))
        return 60.0

    async def _count_issues(self, text: str) -> int:
        issue_patterns = [
            r"问题\d+",
            r"第\d+个问题",
            r"风险\d+",
            r"建议\d+",
        ]
        total = 0
        for pattern in issue_patterns:
            total += len(re.findall(pattern, text, flags=re.IGNORECASE))
        if total > 0:
            return min(total, 50)

        keywords = ["问题", "错误", "风险", "建议", "修复", "改进", "缺陷"]
        approx = sum(text.count(keyword) for keyword in keywords)
        return min(approx, 50)

    async def _format_now(self) -> str:
        return datetime.now(self._tz).strftime("%Y-%m-%d %H:%M:%S")

    async def _generate_error_report(self, error_type: str, error_message: str) -> dict[str, Any]:
        now = await self._format_now()
        return {
            "content": (
                "# ❌ 代码审查报告生成失败\n\n"
                f"- 错误类型: {error_type}\n"
                f"- 错误详情: {error_message}\n"
                f"- 时间: {now}\n"
            ),
            "metadata": {
                "is_mock": False,
                "is_error": True,
                "generated_at": datetime.now(self._tz).isoformat(),
                "error_type": error_type,
                "error_message": error_message,
            },
        }
