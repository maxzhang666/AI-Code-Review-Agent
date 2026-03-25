from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any
from zoneinfo import ZoneInfo

from app.services.notification.channels import truncate_text


def project_name(mr_info: dict[str, Any]) -> str:
    return str(mr_info.get("project_name") or "未知项目")


def mr_title(mr_info: dict[str, Any]) -> str:
    return str(mr_info.get("title") or "代码审查")


def ensure_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        return [item.strip() for item in raw.split(",") if item.strip()]
    return []


def issue_severity_label(severity: str) -> str:
    key = severity.strip().lower()
    mapping = {
        "high": "🔴 高危",
        "medium": "🟡 中危",
        "low": "🟢 低危",
    }
    return mapping.get(key, "🟡 中危")


def issue_location(issue: dict[str, Any]) -> str:
    file_path = str(issue.get("file") or "").strip() or "unknown"
    line = issue.get("line")
    if isinstance(line, int):
        return f"{file_path}:{line}"
    if isinstance(line, str) and line.strip():
        return f"{file_path}:{line.strip()}"
    return file_path


def normalize_multiline(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        return ""
    return normalized.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def issue_code_snippet(issue: dict[str, Any]) -> str:
    raw = str(issue.get("code_snippet") or issue.get("problematic_code") or "")
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.strip():
        return ""
    for line in normalized.split("\n"):
        if line.strip():
            return line
    return ""


def issue_identifier(issue: dict[str, Any], index: int) -> str:
    for key in ("issue_id", "id", "fingerprint"):
        raw = str(issue.get(key) or "").strip()
        if raw:
            return raw[:64]
    return f"I-{index}"


def build_gitlab_comment_message(
    report_data: dict[str, Any],
    mr_info: dict[str, Any],
    tz: ZoneInfo,
) -> str:
    resolved_project_name = project_name(mr_info)
    resolved_mr_title = mr_title(mr_info)
    mr_url = str(mr_info.get("url") or "").strip()
    summary = str(mr_info.get("summary") or "").strip()
    highlights = ensure_str_list(mr_info.get("highlights"))
    issues_raw = mr_info.get("issues")
    issues = issues_raw if isinstance(issues_raw, list) else []
    score = mr_info.get("score")
    score_line = f"{int(score)}/100" if isinstance(score, (int, float)) else "-"
    file_count = int(mr_info.get("file_count") or 0)
    changes_count = int(mr_info.get("changes_count") or 0)

    lines: list[str] = [
        "## 🤖 AI 代码审查结果",
        "",
        f"- **项目**: `{resolved_project_name}`",
        f"- **MR**: [{resolved_mr_title}]({mr_url})" if mr_url else f"- **MR**: {resolved_mr_title}",
        f"- **时间**: {datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}",
        f"- **评分**: {score_line}",
        f"- **文件数**: {file_count} | **变更行数**: {changes_count} | **问题数**: {len(issues)}",
        "",
    ]

    if summary:
        lines.extend([
            "### 📝 审查摘要",
            "",
            summary,
            "",
        ])

    if highlights:
        lines.append("### ✅ 亮点")
        lines.append("")
        for item in highlights:
            lines.append(f"- {item}")
        lines.append("")

    if issues:
        lines.extend([
            f"### ❗ 问题列表（{len(issues)}）",
            "",
        ])
        for idx, raw_issue in enumerate(issues, 1):
            issue = raw_issue if isinstance(raw_issue, dict) else {}
            issue_id = issue_identifier(issue, idx)
            severity = issue_severity_label(str(issue.get("severity") or "medium"))
            category = str(issue.get("category") or "general").strip()
            location = issue_location(issue)
            description = normalize_multiline(str(issue.get("description") or ""))
            suggestion = normalize_multiline(str(issue.get("suggestion") or ""))

            lines.append(f"{idx}. `{issue_id}` {severity} **[{category}]** `{location}`")
            if description:
                lines.append(f"   - 问题: {description}")
            if suggestion:
                lines.append(f"   - 建议: {suggestion}")
            snippet = issue_code_snippet(issue)
            if snippet:
                safe_snippet = snippet.replace("`", "\\`")
                lines.append(f"   - 代码行: `{safe_snippet}`")
            lines.append("")

    return truncate_text("\n".join(lines).strip(), 30000)


def build_plain_text_message(
    report_data: dict[str, Any],
    mr_info: dict[str, Any],
    tz: ZoneInfo,
    limit: int,
) -> str:
    header = (
        "🤖 AI代码审查报告\n\n"
        f"项目: {project_name(mr_info)}\n"
        f"MR: {mr_title(mr_info)}\n"
        f"时间: {datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    )
    content = str(report_data.get("content") or "")
    return truncate_text(header + content, limit)


def build_markdown_message(report_data: dict[str, Any], mr_info: dict[str, Any], tz: ZoneInfo) -> str:
    text = (
        "### 🤖 AI代码审查报告\n\n"
        f"**项目**: {project_name(mr_info)}\n\n"
        f"**MR**: {mr_title(mr_info)}\n\n"
        f"**时间**: {datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "---\n\n"
        f"{str(report_data.get('content') or '')}\n"
    )
    return truncate_text(text, 1500)


def build_html_message(report_data: dict[str, Any], mr_info: dict[str, Any], tz: ZoneInfo) -> str:
    content = escape(str(report_data.get("content") or ""))
    return (
        "<html><body>"
        "<h2>🤖 AI代码审查报告</h2>"
        f"<p><strong>项目:</strong> {escape(project_name(mr_info))}</p>"
        f"<p><strong>MR:</strong> {escape(mr_title(mr_info))}</p>"
        f"<p><strong>时间:</strong> {datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S')}</p>"
        "<hr/>"
        f"<pre style='white-space: pre-wrap; font-family: monospace;'>{content}</pre>"
        "</body></html>"
    )
