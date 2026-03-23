from __future__ import annotations

import asyncio
import os
import shutil
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

from app.config import get_settings
from app.core.logging import get_logger


class RepositoryManager:
    def __init__(self, request_id: str | None = None) -> None:
        self._request_id = request_id
        self._settings = get_settings()
        self._logger = get_logger(__name__, request_id)
        self._base_path = Path(self._settings.REPOSITORY_BASE_PATH)
        self._base_path.mkdir(parents=True, exist_ok=True)

    async def get_or_clone_repository(
        self,
        project_url: str,
        project_id: int,
        access_token: str | None = None,
    ) -> tuple[bool, str | None, str | None]:
        repo_path = self._project_path(project_id)
        if repo_path.exists():
            updated = await self._update_repository(repo_path)
            if updated:
                return True, str(repo_path), None
            await asyncio.to_thread(shutil.rmtree, repo_path, True)

        clone_url = await self._build_authenticated_url(project_url, access_token)
        success, _, stderr = await self._run_git_command(
            ["git", "clone", "--depth", "1", "--no-single-branch", clone_url, str(repo_path)]
        )
        if not success:
            return False, None, f"Failed to clone repository: {stderr}"
        return True, str(repo_path), None

    async def checkout_merge_request(
        self,
        repo_path: str,
        mr_iid: int,
        source_branch: str,
        target_branch: str,
    ) -> tuple[bool, str | None]:
        _ = mr_iid
        path = Path(repo_path)

        success, _, stderr = await self._run_git_command(
            ["git", "checkout", source_branch],
            cwd=path,
        )
        if success:
            await self._run_git_command(["git", "pull", "--ff-only"], cwd=path)
            return True, None

        success, _, stderr = await self._run_git_command(
            ["git", "checkout", "-B", source_branch, f"origin/{source_branch}"],
            cwd=path,
        )
        if success:
            return True, None

        await self._run_git_command(["git", "checkout", target_branch], cwd=path)
        return False, f"Failed to checkout branch {source_branch}: {stderr}"

    async def get_commit_range(
        self,
        repo_path: str,
        target_branch: str,
    ) -> tuple[bool, str | None, str | None]:
        path = Path(repo_path)

        ok, current_branch, stderr = await self._run_git_command(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=path,
        )
        if not ok:
            return False, None, f"Failed to get current branch: {stderr}"

        branch = current_branch.strip()
        ok, merge_base, stderr = await self._run_git_command(
            ["git", "merge-base", f"origin/{target_branch}", branch],
            cwd=path,
        )
        if not ok:
            return True, "HEAD~1..HEAD", None

        return True, f"{merge_base.strip()}..HEAD", None

    async def cleanup_old_repositories(self, days: int | None = None) -> tuple[int, int]:
        keep_days = days if days is not None else self._settings.REPOSITORY_CACHE_DAYS
        cutoff_time = datetime.now() - timedelta(days=keep_days)
        cleaned_count = 0
        freed_bytes = 0

        if not self._base_path.exists():
            return cleaned_count, freed_bytes

        for item in self._base_path.iterdir():
            if not item.is_dir():
                continue

            modified_at = datetime.fromtimestamp(item.stat().st_mtime)
            if modified_at >= cutoff_time:
                continue

            size = await self._directory_size(item)
            await asyncio.to_thread(shutil.rmtree, item, True)
            cleaned_count += 1
            freed_bytes += size

        return cleaned_count, freed_bytes

    async def _run_git_command(
        self,
        command: list[str],
        cwd: Path | None = None,
        timeout: int = 300,
    ) -> tuple[bool, str, str]:
        self._logger.debug(
            "git_command_start",
            command=" ".join(command),
            cwd=str(cwd) if cwd else "",
        )
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(cwd) if cwd else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            return False, "", f"Command timeout after {timeout}s"

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        return process.returncode == 0, stdout, stderr

    async def _update_repository(self, repo_path: Path) -> bool:
        await self._run_git_command(["git", "reset", "--hard"], cwd=repo_path)
        await self._run_git_command(["git", "clean", "-fd"], cwd=repo_path)
        success, _, _ = await self._run_git_command(
            ["git", "fetch", "--all", "--prune"],
            cwd=repo_path,
        )
        return success

    async def _build_authenticated_url(
        self,
        project_url: str,
        access_token: str | None,
    ) -> str:
        if not access_token:
            return project_url
        parsed = urllib.parse.urlparse(project_url)
        if parsed.scheme not in {"http", "https"}:
            return project_url

        token = urllib.parse.quote(access_token, safe="")
        hostname = parsed.netloc
        path = parsed.path.lstrip("/")
        return f"{parsed.scheme}://oauth2:{token}@{hostname}/{path}"

    async def _directory_size(self, path: Path) -> int:
        def _walk_size() -> int:
            total = 0
            for root, _, files in os.walk(path):
                for file_name in files:
                    file_path = Path(root) / file_name
                    if file_path.exists():
                        total += file_path.stat().st_size
            return total

        return await asyncio.to_thread(_walk_size)

    def _project_path(self, project_id: int) -> Path:
        return self._base_path / f"project-{project_id}"
