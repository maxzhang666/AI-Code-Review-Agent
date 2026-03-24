from __future__ import annotations

from app.services.notification import NotificationDispatcher


def test_gitlab_comment_message_renders_structured_issue_list() -> None:
    dispatcher = NotificationDispatcher(request_id="req-test")

    report_data = {
        "content": "# 原始报告\n\n更多细节",
    }
    mr_info = {
        "project_name": "demo-project",
        "title": "fix: handle null pointer",
        "url": "https://gitlab.example.com/group/demo/-/merge_requests/12",
        "score": 88,
        "file_count": 3,
        "changes_count": 128,
        "summary": "整体质量较好，但存在空指针风险。",
        "highlights": ["结构清晰", "日志增强"],
        "issues": [
            {
                "severity": "high",
                "category": "reliability",
                "file": "src/main/java/Foo.java",
                "line": 42,
                "description": "可能出现空指针异常",
                "suggestion": "增加非空判断\n并补充单测",
                "code_snippet": "if (foo == null) {\n    return bar.toString();\n}",
            }
        ],
    }

    message = dispatcher._gitlab_comment_message(report_data, mr_info)

    assert "## 🤖 AI 代码审查结果" in message
    assert "### 📝 审查摘要" in message
    assert "### ✅ 亮点" in message
    assert "### ❗ 问题列表（1）" in message
    assert "1. 🔴 高危 **[reliability]** `src/main/java/Foo.java:42`" in message
    assert "问题: 可能出现空指针异常" in message
    assert "建议: 增加非空判断<br>并补充单测" in message
    assert "代码行:" in message
    assert "if (foo == null) {" in message
    assert "return bar.toString();" not in message
    assert "```" not in message
    assert "<details>" not in message
    assert "查看完整审查报告" not in message


def test_gitlab_comment_message_handles_missing_issue_fields() -> None:
    dispatcher = NotificationDispatcher(request_id="req-test")

    message = dispatcher._gitlab_comment_message(
        report_data={"content": ""},
        mr_info={
            "project_name": "demo-project",
            "title": "refactor",
            "issues": [{"description": "描述"}],
        },
    )

    assert "问题列表（1）" in message
    assert "`unknown`" in message
    assert "问题: 描述" in message


def test_gitlab_comment_message_uses_problematic_code_alias_for_snippet() -> None:
    dispatcher = NotificationDispatcher(request_id="req-test")

    message = dispatcher._gitlab_comment_message(
        report_data={"content": ""},
        mr_info={
            "project_name": "demo-project",
            "title": "fix: alias snippet",
            "issues": [
                {
                    "severity": "medium",
                    "category": "Bug",
                    "file": "app/main.py",
                    "line": 7,
                    "description": "key 访问未判空",
                    "problematic_code": "return payload['data']['id']",
                }
            ],
        },
    )

    assert "代码行:" in message
    assert "return payload['data']['id']" in message
