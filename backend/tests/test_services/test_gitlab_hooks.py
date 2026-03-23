from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services.gitlab import GitLabService


class _FakeHookManager:
    def __init__(self, hooks: list[SimpleNamespace]) -> None:
        self._hooks = hooks
        self.created_payloads: list[dict] = []

    def list(self, **_kwargs):
        return self._hooks

    def create(self, payload: dict) -> SimpleNamespace:
        self.created_payloads.append(payload)
        return SimpleNamespace(id=999)


class _FakeProjects:
    def __init__(self, hook_manager: _FakeHookManager) -> None:
        self._hook_manager = hook_manager

    def get(self, _project_id: int) -> SimpleNamespace:
        return SimpleNamespace(hooks=self._hook_manager)


class _FakeClient:
    def __init__(self, hook_manager: _FakeHookManager) -> None:
        self.projects = _FakeProjects(hook_manager)


@pytest.mark.asyncio
async def test_create_project_hook_skips_when_same_url_exists(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hook_manager = _FakeHookManager(
        hooks=[SimpleNamespace(id=123, url="https://site.example/api/webhook/gitlab/")]
    )
    svc = GitLabService(db_session)

    async def _fake_ensure_client():
        return _FakeClient(hook_manager)

    monkeypatch.setattr(svc, "_ensure_client", _fake_ensure_client)

    result = await svc.create_project_hook(1, "https://site.example/api/webhook/gitlab")

    assert result["success"] is True
    assert result["hook_id"] == 123
    assert result["already_exists"] is True
    assert hook_manager.created_payloads == []


@pytest.mark.asyncio
async def test_create_project_hook_creates_when_url_not_exists(
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hook_manager = _FakeHookManager(
        hooks=[SimpleNamespace(id=123, url="https://site.example/other-webhook")]
    )
    svc = GitLabService(db_session)

    async def _fake_ensure_client():
        return _FakeClient(hook_manager)

    monkeypatch.setattr(svc, "_ensure_client", _fake_ensure_client)

    result = await svc.create_project_hook(1, "https://site.example/api/webhook/gitlab/")

    assert result["success"] is True
    assert result["hook_id"] == 999
    assert result["already_exists"] is False
    assert hook_manager.created_payloads == [
        {
            "url": "https://site.example/api/webhook/gitlab/",
            "merge_requests_events": True,
            "push_events": False,
            "enable_ssl_verification": True,
        }
    ]
