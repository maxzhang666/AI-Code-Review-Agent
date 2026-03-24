from __future__ import annotations

import json
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE_PATH = PROJECT_ROOT / ".env"

DEFAULT_GPT_MESSAGE = """\
请帮我 code review 最近一次提交的内容，从以下角度分析：
1. 代码质量和最佳实践
2. 潜在的 bug 和安全问题
3. 性能优化建议
4. 代码风格和可读性

你必须严格返回以下JSON格式（不要包裹在markdown代码块中，直接返回纯JSON）：

{
  "score": 85,
  "summary": "一段简洁的审查摘要，概述代码整体质量",
  "highlights": ["代码优点1", "代码优点2"],
  "issues": [
    {
      "severity": "high",
      "category": "Bug",
      "file": "path/to/file.py",
      "line": 42,
      "description": "问题描述",
      "suggestion": "修改建议或修改后的代码示例",
      "code_snippet": "有问题的原始代码片段（尽量精简）"
    }
  ]
}

字段说明：
- score: 0~100的整数评分
- summary: 审查摘要
- highlights: 代码优点列表
- issues: 问题列表，每个问题包含：
  - severity: "high"（严重）、"medium"（中等）、"low"（轻微）
  - category: "安全"、"性能"、"质量"、"风格"、"Bug" 之一
  - file: 问题所在文件路径
  - line: 问题所在行号（无法确定时为null）
  - description: 以精炼语言、严厉语气描述问题
  - suggestion: 具体修改建议，可包含代码示例
  - code_snippet: 触发问题的原始代码片段（没有可留空字符串）

要求：
1. 以精炼的语言、严厉的语气指出存在的问题
2. 无问题时issues为空数组，不要编造问题
3. 只返回JSON，不要附加任何其他文字"""

DEFAULT_CLAUDE_CLI_PROMPT = """\
请帮我 code review 最近一次提交的内容，从以下角度分析：
1. 代码质量和最佳实践
2. 潜在的 bug 和安全问题
3. 性能优化建议
4. 代码风格和可读性

你必须严格返回以下JSON格式（不要包裹在markdown代码块中，直接返回纯JSON）：

{
  "score": 85,
  "summary": "一段简洁的审查摘要",
  "highlights": ["代码优点1", "代码优点2"],
  "issues": [
    {
      "severity": "high|medium|low",
      "category": "安全|性能|质量|风格|Bug",
      "file": "path/to/file.py",
      "line": 42,
      "description": "问题描述",
      "suggestion": "修改建议",
      "code_snippet": "有问题的原始代码片段（没有可留空）"
    }
  ]
}

要求：只返回JSON，不要附加任何其他文字。无问题时issues为空数组。"""


class TaskQueueBackend(str, Enum):
    memory = "memory"
    redis = "redis"
    database = "database"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./db.sqlite3"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Server
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5175",
            "http://127.0.0.1:5175",
        ]
    )
    TIMEZONE: str = "Asia/Shanghai"
    PAGE_SIZE: int = 100

    # Auth
    AUTH_BOOTSTRAP_USERNAME: str = "admin"
    AUTH_BOOTSTRAP_PASSWORD: str = "admin123456"
    AUTH_TOKEN_EXPIRE_HOURS: int = 12

    # Repository
    REPOSITORY_BASE_PATH: str = "./data/repositories"
    REPOSITORY_CACHE_DAYS: int = 7
    REPOSITORY_MAX_SIZE_GB: int = 50

    # File filtering defaults (exclude non-source artifacts by default)
    EXCLUDE_FILE_TYPES: list[str] = Field(
        default_factory=lambda: [".sql", ".dump", ".lock", ".log", ".tmp", ".bak" ,".Designer.cs"]
    )
    IGNORE_FILE_TYPES: list[str] = Field(
        default_factory=lambda: [".md", ".txt", ".json", ".xml", ".yml", ".yaml"]
    )

    # Task Queue
    TASK_QUEUE_BACKEND: TaskQueueBackend = TaskQueueBackend.memory

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"
    LOG_FILE_MAX_BYTES: int = 2 * 1024 * 1024
    LOG_FILE_BACKUP_COUNT: int = 10

    # Review prompt
    GPT_MESSAGE: str = DEFAULT_GPT_MESSAGE
    CLAUDE_CLI_DEFAULT_PROMPT: str = DEFAULT_CLAUDE_CLI_PROMPT
    REVIEW_CODE_SNIPPET_SOURCE: str = "line"

    @field_validator("CORS_ORIGINS", "EXCLUDE_FILE_TYPES", "IGNORE_FILE_TYPES", mode="before")
    @classmethod
    def _parse_string_list(cls, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, list):
                    return [str(v).strip() for v in parsed if str(v).strip()]
            return [v.strip() for v in raw.split(",") if v.strip()]
        raise TypeError("Expected list[str] or comma-separated string.")

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: Any) -> str:
        return value.upper() if isinstance(value, str) else "INFO"

    @field_validator("REVIEW_CODE_SNIPPET_SOURCE", mode="before")
    @classmethod
    def _normalize_review_code_snippet_source(cls, value: Any) -> str:
        normalized = str(value or "").strip().lower()
        if normalized in {"line", "llm"}:
            return normalized
        raise ValueError("REVIEW_CODE_SNIPPET_SOURCE must be either 'line' or 'llm'")

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: Any) -> str:
        if not isinstance(value, str):
            return "sqlite+aiosqlite:///./db.sqlite3"
        raw = value.strip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
            raw = raw[1:-1].strip()
        return raw or "sqlite+aiosqlite:///./db.sqlite3"

    @field_validator(
        "REPOSITORY_CACHE_DAYS",
        "REPOSITORY_MAX_SIZE_GB",
        "PAGE_SIZE",
        "LOG_FILE_MAX_BYTES",
        "LOG_FILE_BACKUP_COUNT",
        "AUTH_TOKEN_EXPIRE_HOURS",
    )
    @classmethod
    def _positive_integer(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Value must be > 0")
        return value

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.lower().startswith("sqlite")

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.lower().startswith("postgresql")

    def ensure_directories(self) -> None:
        Path(self.LOG_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.REPOSITORY_BASE_PATH).mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
