from __future__ import annotations

from app.services.review_structured import enrich_issues_with_code_snippets


def test_enrich_issues_uses_line_based_snippet_by_default() -> None:
    changes = [
        {
            "new_path": "src/core.py",
            "diff": (
                "@@ -1,3 +1,4 @@\n"
                " def build(payload):\n"
                "-    return payload['meta']['id']\n"
                "+    meta = payload.get('meta')\n"
                "+    return meta['id']\n"
            ),
        }
    ]
    issues = [
        {
            "file": "src/core.py",
            "line": 3,
            "description": "possible key error",
            "code_snippet": "LLM snippet should be fallback only",
        }
    ]

    enriched = enrich_issues_with_code_snippets(issues, changes=changes, source_mode="line")

    assert len(enriched) == 1
    assert enriched[0]["code_snippet"] == "    return meta['id']"


def test_enrich_issues_line_mode_falls_back_to_llm_snippet() -> None:
    changes = [{"new_path": "src/core.py", "diff": "@@ -1,1 +1,1 @@\n+print('ok')\n"}]
    issues = [
        {
            "file": "src/core.py",
            "line": 99,
            "description": "no matching line in diff",
            "code_snippet": "fallback from llm\nsecond line should be dropped",
        }
    ]

    enriched = enrich_issues_with_code_snippets(issues, changes=changes, source_mode="line")

    assert len(enriched) == 1
    assert enriched[0]["code_snippet"] == "fallback from llm"


def test_enrich_issues_llm_mode_prefers_llm_snippet() -> None:
    changes = [
        {
            "new_path": "src/core.py",
            "diff": (
                "@@ -1,3 +1,4 @@\n"
                " def build(payload):\n"
                "-    return payload['meta']['id']\n"
                "+    meta = payload.get('meta')\n"
                "+    return meta['id']\n"
            ),
        }
    ]
    issues = [
        {
            "file": "src/core.py",
            "line": 3,
            "description": "possible key error",
            "code_snippet": "LLM provided snippet\nextra context line",
        }
    ]

    enriched = enrich_issues_with_code_snippets(issues, changes=changes, source_mode="llm")

    assert len(enriched) == 1
    assert enriched[0]["code_snippet"] == "LLM provided snippet"
