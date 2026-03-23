from __future__ import annotations

import asyncio
from typing import Any

import gitlab
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from app.core.logging import get_logger
from app.models import GitLabConfig


class GitLabService:
    def __init__(self, db: AsyncSession, request_id: str | None = None) -> None:
        self._db = db
        self._request_id = request_id
        self._logger = get_logger(__name__, request_id)
        self._client: gitlab.Gitlab | None = None
        self._server_url: str | None = None
        self._private_token: str | None = None

    async def _load_config(self, db: AsyncSession | None = None) -> GitLabConfig:
        session = db or self._db
        stmt = (
            select(GitLabConfig)
            .where(GitLabConfig.is_active.is_(True))
            .order_by(GitLabConfig.updated_at.desc())
            .limit(1)
        )
        config = (await session.execute(stmt)).scalars().first()
        if config is None:
            raise RuntimeError("No active GitLab configuration found.")

        self._server_url = config.server_url
        self._private_token = config.private_token
        return config

    def _init_client(self) -> gitlab.Gitlab:
        if not self._server_url or not self._private_token:
            raise RuntimeError("GitLab client configuration is incomplete.")
        return gitlab.Gitlab(
            self._server_url,
            private_token=self._private_token,
            timeout=30,
        )

    async def _ensure_client(self) -> gitlab.Gitlab:
        if self._client is not None:
            return self._client

        await self._load_config()
        client = self._init_client()
        await asyncio.to_thread(client.auth)
        self._client = client
        return client

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(Exception),
    )
    async def get_merge_request_changes(
        self,
        project_id: int,
        mr_iid: int,
    ) -> dict[str, Any]:
        client = await self._ensure_client()

        def _sync_call() -> dict[str, Any]:
            project = client.projects.get(project_id)
            merge_request = project.mergerequests.get(mr_iid)
            return merge_request.changes()

        try:
            return await asyncio.to_thread(_sync_call)
        except Exception as exc:
            self._logger.log_error_with_context(
                "gitlab_get_merge_request_changes_failed",
                error=exc,
                project_id=project_id,
                mr_iid=mr_iid,
            )
            raise

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(Exception),
    )
    async def get_merge_request_info(
        self,
        project_id: int,
        mr_iid: int,
    ) -> dict[str, Any]:
        client = await self._ensure_client()

        def _sync_call() -> dict[str, Any]:
            project = client.projects.get(project_id)
            merge_request = project.mergerequests.get(mr_iid)
            return merge_request.asdict()

        try:
            return await asyncio.to_thread(_sync_call)
        except Exception as exc:
            self._logger.log_error_with_context(
                "gitlab_get_merge_request_info_failed",
                error=exc,
                project_id=project_id,
                mr_iid=mr_iid,
            )
            raise

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(Exception),
    )
    async def get_file_content(
        self,
        project_id: int,
        file_path: str,
        branch: str,
    ) -> str:
        client = await self._ensure_client()

        def _sync_call() -> str:
            project = client.projects.get(project_id)
            file_obj = project.files.get(file_path=file_path, ref=branch)
            return file_obj.decode()

        try:
            return await asyncio.to_thread(_sync_call)
        except Exception as exc:
            self._logger.log_error_with_context(
                "gitlab_get_file_content_failed",
                error=exc,
                project_id=project_id,
                branch=branch,
                file_path=file_path,
            )
            raise

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(Exception),
    )
    async def post_merge_request_comment(
        self,
        project_id: int,
        mr_iid: int,
        comment: str,
    ) -> dict[str, Any]:
        client = await self._ensure_client()

        def _sync_call() -> dict[str, Any]:
            project = client.projects.get(project_id)
            merge_request = project.mergerequests.get(mr_iid)
            note = merge_request.notes.create({"body": comment})
            return note.asdict()

        try:
            result = await asyncio.to_thread(_sync_call)
            self._logger.info(
                "gitlab_comment_posted",
                project_id=project_id,
                mr_iid=mr_iid,
                note_id=result.get("id"),
            )
            return result
        except Exception as exc:
            self._logger.log_error_with_context(
                "gitlab_post_merge_request_comment_failed",
                error=exc,
                project_id=project_id,
                mr_iid=mr_iid,
            )
            raise

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(Exception),
    )
    async def get_project_info(self, project_id: int) -> dict[str, Any]:
        client = await self._ensure_client()

        def _sync_call() -> dict[str, Any]:
            project = client.projects.get(project_id)
            return project.asdict()

        try:
            return await asyncio.to_thread(_sync_call)
        except Exception as exc:
            self._logger.log_error_with_context(
                "gitlab_get_project_info_failed",
                error=exc,
                project_id=project_id,
            )
            raise

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(Exception),
    )
    async def list_projects(
        self,
        search: str = "",
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        client = await self._ensure_client()

        def _sync_call() -> tuple[list[dict[str, Any]], int]:
            kwargs: dict[str, Any] = {
                "page": page,
                "per_page": per_page,
                "membership": True,
                "order_by": "created_at",
                "sort": "desc",
            }
            if search:
                kwargs["search"] = search

            result = client.projects.list(**kwargs)
            total = int(result.total or 0) if hasattr(result, "total") else 0
            items = []
            for proj in result:
                ns = proj.namespace or {}
                items.append({
                    "id": proj.id,
                    "name": proj.name,
                    "path_with_namespace": proj.path_with_namespace,
                    "web_url": proj.web_url,
                    "namespace": ns.get("full_path", "") if isinstance(ns, dict) else str(ns),
                    "description": proj.description or "",
                    "last_activity_at": getattr(proj, "last_activity_at", None),
                })
            return items, total

        try:
            return await asyncio.to_thread(_sync_call)
        except Exception as exc:
            self._logger.log_error_with_context(
                "gitlab_list_projects_failed",
                error=exc,
                search=search,
            )
            raise

    async def create_project_hook(
        self,
        project_id: int,
        webhook_url: str,
    ) -> dict[str, Any]:
        client = await self._ensure_client()
        normalized_url = webhook_url.strip().rstrip("/")

        def _sync_call() -> dict[str, Any]:
            project = client.projects.get(project_id)
            existing_hooks = project.hooks.list(all=True)
            for existing_hook in existing_hooks:
                existing_url = str(getattr(existing_hook, "url", "")).strip().rstrip("/")
                if existing_url and existing_url == normalized_url:
                    return {
                        "success": True,
                        "hook_id": getattr(existing_hook, "id", None),
                        "already_exists": True,
                    }

            hook = project.hooks.create({
                "url": webhook_url,
                "merge_requests_events": True,
                "push_events": False,
                "enable_ssl_verification": True,
            })
            return {"success": True, "hook_id": hook.id, "already_exists": False}

        try:
            return await asyncio.to_thread(_sync_call)
        except Exception as exc:
            self._logger.log_error_with_context(
                "gitlab_create_project_hook_failed",
                error=exc,
                project_id=project_id,
            )
            return {"success": False, "error": str(exc)}
