from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any
from urllib.parse import urlparse, urlunparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.logging import PipelineTracer, get_logger
from app.database import get_session_factory
from app.llm import llm_router
from app.llm.types import LLMRequest
from app.models import (
    LLMProvider,
    MergeRequestReview,
    Project,
    ProjectWebhookEventPrompt,
    WebhookEventRule,
    WebhookLog,
)
from app.services.gitlab import GitLabService
from app.services.notification import NotificationDispatcher
from app.services.report import ReportGenerator
from app.services.repository import RepositoryManager
from app.services.review import ReviewResultParser, ReviewService
from app.services.review_structured import normalize_issues, replace_review_findings

TaskHandler = Callable[[dict[str, Any]], Awaitable[Any] | Any]
_TASK_REGISTRY: dict[str, TaskHandler] = {}
_TRACE_PREVIEW_LIMIT = 8000


def register_task(task_type: str) -> Callable[[TaskHandler], TaskHandler]:
    def decorator(func: TaskHandler) -> TaskHandler:
        _TASK_REGISTRY[task_type] = func
        return func

    return decorator


def get_handler(task_type: str) -> TaskHandler | None:
    return _TASK_REGISTRY.get(task_type)


def _as_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _count_changed_lines(changes: list[dict[str, Any]]) -> int:
    total = 0
    for change in changes:
        diff = str(change.get("diff") or "")
        for line in diff.splitlines():
            if line.startswith("+++ ") or line.startswith("--- "):
                continue
            if line.startswith("+") or line.startswith("-"):
                total += 1
    return total


def _normalize_clone_url(project_url: str, server_url: str) -> str:
    parsed_server = urlparse(server_url.rstrip("/"))
    parsed_project = urlparse(project_url)
    return urlunparse((
        parsed_server.scheme,
        parsed_server.netloc,
        parsed_project.path,
        parsed_project.params,
        parsed_project.query,
        parsed_project.fragment,
    ))


def _resolve_max_tokens(value: Any, default: int = 20480) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if parsed <= 0:
        return default
    return parsed


def _truncate_trace_text(value: Any, limit: int = _TRACE_PREVIEW_LIMIT) -> tuple[str, bool]:
    text = str(value or "")
    if len(text) <= limit:
        return text, False
    return text[:limit], True


def _serialize_trace_payload(value: Any, limit: int = _TRACE_PREVIEW_LIMIT) -> tuple[str, bool]:
    if value is None:
        return "{}", False
    if isinstance(value, str):
        return _truncate_trace_text(value, limit=limit)
    try:
        text = json.dumps(value, ensure_ascii=False, default=str)
    except Exception:
        text = str(value)
    return _truncate_trace_text(text, limit=limit)


def _serialize_notification_results(results: Any, limit: int = _TRACE_PREVIEW_LIMIT) -> tuple[str, bool]:
    if not isinstance(results, list):
        return "[]", False

    normalized: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        details_raw = item.get("details")
        details = details_raw if isinstance(details_raw, dict) else {}
        normalized.append(
            {
                "channel": item.get("channel"),
                "channel_name": item.get("channel_name"),
                "success": bool(item.get("success")),
                "message": str(item.get("message") or ""),
                "response_time": item.get("response_time"),
                "status_code": details.get("status_code"),
                "details": details,
            }
        )

    return _serialize_trace_payload(normalized, limit=limit)


def _notification_channel_step_name(channel_name: Any, channel_type: Any, index: int) -> str:
    label = str(channel_name or channel_type or f"channel-{index + 1}").strip()
    if not label:
        label = f"channel-{index + 1}"
    sanitized = label.replace("\r", " ").replace("\n", " ")
    return f"notification_dispatch:{sanitized}"


async def _find_project(db: AsyncSession, project_id: int) -> Project | None:
    stmt = select(Project).where(Project.project_id == project_id).limit(1)
    return (await db.execute(stmt)).scalars().first()


async def _find_event_rule(
    db: AsyncSession,
    event_type: str,
    payload: dict[str, Any],
    enabled_rule_ids: list[int],
) -> WebhookEventRule | None:
    stmt = select(WebhookEventRule).where(WebhookEventRule.is_active.is_(True))
    if event_type:
        stmt = stmt.where(WebhookEventRule.event_type == event_type)
    rules = list((await db.execute(stmt)).scalars().all())

    if not rules and event_type:
        fallback_stmt = select(WebhookEventRule).where(WebhookEventRule.is_active.is_(True))
        rules = list((await db.execute(fallback_stmt)).scalars().all())

    enabled_set = {_as_int(item) for item in enabled_rule_ids}
    enabled_set.discard(None)
    if enabled_set:
        rules = [rule for rule in rules if rule.id in enabled_set]

    for rule in rules:
        if rule.matches_payload(payload):
            return rule
    return None


async def _resolve_custom_prompt(
    db: AsyncSession,
    project_pk: int,
    event_rule_id: int,
    context: dict[str, Any],
) -> str | None:
    stmt = (
        select(ProjectWebhookEventPrompt)
        .where(
            ProjectWebhookEventPrompt.project_id == project_pk,
            ProjectWebhookEventPrompt.event_rule_id == event_rule_id,
            ProjectWebhookEventPrompt.use_custom.is_(True),
        )
        .limit(1)
    )
    prompt_config = (await db.execute(stmt)).scalars().first()
    if prompt_config is None or not prompt_config.custom_prompt:
        return None
    rendered = prompt_config.render_prompt(context).strip()
    return rendered or None


@register_task("review_mr")
async def review_merge_request(data: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    payload = data.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("Task payload must contain a JSON object in `data.payload`.")

    project_ref = payload.get("project")
    project_id = _as_int(data.get("project_id"))
    if project_id is None and isinstance(project_ref, dict):
        project_id = _as_int(project_ref.get("id"))
    if project_id is None:
        project_id = _as_int(payload.get("project_id"))
    if project_id is None:
        raise ValueError("Missing project_id in task payload.")

    webhook_log_id = _as_int(data.get("webhook_log_id"))
    request_id = str(data.get("request_id") or "").strip() or None
    event_type = str(
        data.get("event_type")
        or payload.get("event_type")
        or payload.get("object_kind")
        or "Unknown Event"
    )

    logger = get_logger(__name__, request_id)
    tracer = PipelineTracer(logger)
    session_factory = get_session_factory()
    review_id: int | None = None
    tracked_webhook_log_id = webhook_log_id
    mr_title = ""
    mr_description = ""
    author_name = "unknown"
    author_email = ""
    mr_iid: int | None = None
    source_branch = ""
    target_branch = ""
    mr_url = ""

    try:
        async with session_factory() as db:
            project = await _find_project(db, project_id)
            if project is None:
                raise RuntimeError(f"Project not found for project_id={project_id}.")

            tracer.step("project_found", project_name=project.project_name)

            webhook_log = await db.get(WebhookLog, webhook_log_id) if webhook_log_id else None
            if webhook_log is not None and tracked_webhook_log_id is None:
                tracked_webhook_log_id = webhook_log.id

            event_rule = await _find_event_rule(
                db=db,
                event_type=event_type,
                payload=payload,
                enabled_rule_ids=list(project.enabled_webhook_events or []),
            )
            if event_rule is None:
                tracer.step(
                    "event_rule_unmatched",
                    status="warning",
                    event_type=event_type,
                    enabled_rule_count=len(list(project.enabled_webhook_events or [])),
                )
                if webhook_log is not None:
                    webhook_log.pipeline_trace = tracer.to_dict()
                    webhook_log.processed = True
                    webhook_log.processed_at = datetime.now()
                    webhook_log.log_level = "WARNING"
                    webhook_log.skip_reason = "No matching active webhook event rule."
                    webhook_log.error_message = None
                await db.commit()
                return {
                    "status": "skipped",
                    "reason": "no_matching_event_rule",
                    "project_id": project.project_id,
                    "webhook_log_id": tracked_webhook_log_id,
                }

            tracer.step(
                "event_rule_matched",
                rule_id=event_rule.id,
                rule_name=event_rule.name,
                rule_event_type=event_rule.event_type,
            )

            if not project.review_enabled:
                tracer.step(
                    "project_review_disabled",
                    status="warning",
                    project_id=project.project_id,
                    project_name=project.project_name,
                )
                if webhook_log is not None:
                    webhook_log.pipeline_trace = tracer.to_dict()
                    webhook_log.processed = True
                    webhook_log.processed_at = datetime.now()
                    webhook_log.log_level = "WARNING"
                    webhook_log.skip_reason = "Project review is disabled."
                    webhook_log.error_message = None
                await db.commit()
                return {
                    "status": "skipped",
                    "reason": "project_review_disabled",
                    "project_id": project.project_id,
                    "webhook_log_id": tracked_webhook_log_id,
                }

            attrs = payload.get("object_attributes")
            attrs = attrs if isinstance(attrs, dict) else {}
            user = payload.get("user")
            user = user if isinstance(user, dict) else {}

            mr_iid = _as_int(attrs.get("iid"))
            if mr_iid is None and webhook_log is not None:
                mr_iid = webhook_log.merge_request_iid
            if mr_iid is None:
                raise RuntimeError("Missing merge request IID in webhook payload.")

            source_branch = str(attrs.get("source_branch") or webhook_log.source_branch if webhook_log else "")
            target_branch = str(attrs.get("target_branch") or webhook_log.target_branch if webhook_log else "")
            mr_title = str(attrs.get("title") or attrs.get("last_commit", {}).get("message") or "")
            mr_description = str(attrs.get("description") or "")
            author_name = str(user.get("name") or webhook_log.user_name if webhook_log else "unknown")
            author_email = str(user.get("email") or webhook_log.user_email if webhook_log else "")
            mr_url = str(attrs.get("url") or "")
            tracer.step(
                "mr_context_parsed",
                event_type=event_type,
                mr_iid=mr_iid,
                source_branch=source_branch,
                target_branch=target_branch,
                author=author_name,
            )

            review = MergeRequestReview(
                project_id=project.project_id,
                project_name=project.project_name,
                merge_request_iid=mr_iid,
                merge_request_title=mr_title[:500],
                source_branch=source_branch[:255],
                target_branch=target_branch[:255],
                author_name=author_name[:255],
                author_email=author_email[:255],
                review_content="",
                review_score=None,
                files_reviewed=[],
                total_files=0,
                status="processing",
                request_id=request_id,
            )
            db.add(review)
            await db.flush()
            review_id = review.id
            await db.commit()
            tracer.step("review_record_created", review_id=review_id)

            provider: LLMProvider = await llm_router.resolve_provider(project.project_id, db)
            tracer.step(
                "provider_resolved",
                provider=provider.name, protocol=provider.protocol,
            )
            gitlab_service = GitLabService(db=db, request_id=request_id)
            review_service = ReviewService(request_id=request_id)
            report_generator = ReportGenerator(request_id=request_id)
            notifier = NotificationDispatcher(request_id=request_id)

            files_reviewed: list[str] = []
            total_files = 0
            changes_count = 0
            review_score: int | None = None
            review_issues: list[dict[str, Any]] = []
            review_summary = ""
            review_highlights: list[str] = []
            filter_summary: dict[str, Any] = {}
            llm_text = ""
            llm_model = (
                str((provider.config_data or {}).get("model"))
                if isinstance(provider.config_data, dict)
                else ""
            ) or provider.name
            provider_max_tokens = _resolve_max_tokens(
                (provider.config_data or {}).get("max_tokens") if isinstance(provider.config_data, dict) else None
            )

            prompt_context = {
                "project_name": project.project_name,
                "project_id": project.project_id,
                "author": author_name,
                "title": mr_title,
                "description": mr_description,
                "source_branch": source_branch,
                "target_branch": target_branch,
                "mr_iid": mr_iid,
                "file_count": 0,
                "changes_count": 0,
            }

            if provider.protocol == "mock":
                tracer.step("mock_mode_skip_llm")
            elif provider.protocol == "claude_cli":
                repository_manager = RepositoryManager(request_id=request_id)
                gitlab_cfg = await gitlab_service._load_config(db)
                access_token = gitlab_cfg.private_token if gitlab_cfg.private_token else None
                clone_url = _normalize_clone_url(project.project_url, gitlab_cfg.server_url)

                async with tracer.timed_step("clone_repository"):
                    ok, repo_path, clone_error = await repository_manager.get_or_clone_repository(
                        project_url=clone_url,
                        project_id=project.project_id,
                        access_token=access_token,
                    )
                if not ok or not repo_path:
                    raise RuntimeError(clone_error or "Repository clone failed.")

                async with tracer.timed_step("checkout_branch"):
                    ok, checkout_error = await repository_manager.checkout_merge_request(
                        repo_path=repo_path,
                        mr_iid=mr_iid,
                        source_branch=source_branch,
                        target_branch=target_branch,
                    )
                if not ok:
                    raise RuntimeError(checkout_error or "Repository checkout failed.")

                ok, commit_range, range_error = await repository_manager.get_commit_range(
                    repo_path=repo_path,
                    target_branch=target_branch,
                )
                if not ok:
                    logger.warning("commit_range_fallback", error=range_error or "Failed to compute commit range")
                    commit_range = "HEAD~1..HEAD"
                tracer.step("commit_range", range=commit_range)

                custom_prompt = await _resolve_custom_prompt(
                    db=db,
                    project_pk=project.id,
                    event_rule_id=event_rule.id,
                    context=prompt_context,
                )
                tracer.step(
                    "custom_prompt_resolved",
                    use_custom=bool(custom_prompt),
                    prompt_length=len(custom_prompt) if custom_prompt else 0,
                )

                prompt = (custom_prompt or settings.CLAUDE_CLI_DEFAULT_PROMPT).strip()
                prompt = (
                    f"{prompt}\n\n"
                    f"Project: {project.project_name}\n"
                    f"Merge Request IID: {mr_iid}\n"
                    f"Source Branch: {source_branch}\n"
                    f"Target Branch: {target_branch}\n"
                    f"Commit Range: {commit_range or 'HEAD~1..HEAD'}"
                )
                tracer.step(
                    "llm_request_payload",
                    protocol="claude_cli",
                    model=llm_model,
                    max_tokens=provider_max_tokens,
                    prompt_length=len(prompt),
                    prompt_preview=prompt,
                    prompt_preview_truncated=False,
                    system_message_length=len(settings.GPT_MESSAGE),
                    system_message_preview=settings.GPT_MESSAGE,
                    system_message_preview_truncated=False,
                )
                llm_request = LLMRequest(
                    prompt=prompt,
                    system_message=settings.GPT_MESSAGE,
                    repo_path=repo_path,
                    max_tokens=provider_max_tokens,
                )
                async with tracer.timed_step("llm_review", protocol="claude_cli"):
                    llm_response = await llm_router.review(provider, llm_request)
                llm_text = llm_response.content
                llm_model = llm_response.model or llm_model
                tracer.step(
                    "llm_response_payload",
                    protocol="claude_cli",
                    model=llm_model,
                    duration_ms=llm_response.duration_ms,
                    content_length=len(llm_text),
                    content_preview=llm_text,
                    content_preview_truncated=False,
                )
                parsed = ReviewResultParser.parse(llm_text)
                score_raw = parsed.get("score")
                if isinstance(score_raw, int):
                    review_score = score_raw
                review_issues = parsed.get("issues", [])
                review_summary = parsed.get("summary", "")
                review_highlights = parsed.get("highlights", [])
            else:
                async with tracer.timed_step("get_mr_changes"):
                    changes_result = await gitlab_service.get_merge_request_changes(
                        project_id=project.project_id,
                        mr_iid=mr_iid,
                    )
                raw_changes = changes_result.get("changes", []) if isinstance(changes_result, dict) else []
                changes = raw_changes if isinstance(raw_changes, list) else []
                files_reviewed = [
                    str(item.get("new_path") or item.get("old_path") or "")
                    for item in changes
                    if isinstance(item, dict)
                ]
                files_reviewed = [item for item in files_reviewed if item]
                total_files = len(files_reviewed)
                changes_count = _count_changed_lines(changes)
                prompt_context["file_count"] = total_files
                prompt_context["changes_count"] = changes_count

                tracer.step(
                    "changes_fetched",
                    total_files=total_files, changes_count=changes_count,
                )

                custom_prompt = await _resolve_custom_prompt(
                    db=db,
                    project_pk=project.id,
                    event_rule_id=event_rule.id,
                    context=prompt_context,
                )
                tracer.step(
                    "custom_prompt_resolved",
                    use_custom=bool(custom_prompt),
                    prompt_length=len(custom_prompt) if custom_prompt else 0,
                )

                payload_for_review = dict(payload)
                if custom_prompt:
                    payload_for_review["custom_prompt"] = custom_prompt
                review_result = await review_service.review_merge_request(changes, payload_for_review, db)
                llm_text = str(review_result.get("content") or "")
                score_raw = review_result.get("score")
                if isinstance(score_raw, (int, float)):
                    review_score = int(score_raw)
                review_issues = review_result.get("issues", [])
                review_summary = review_result.get("summary", "")
                review_highlights = review_result.get("highlights", [])
                llm_model = str(review_result.get("llm_model") or llm_model)
                llm_trace_raw = review_result.get("llm_trace")
                llm_request_trace = llm_trace_raw.get("request") if isinstance(llm_trace_raw, dict) else None
                llm_response_trace = llm_trace_raw.get("response") if isinstance(llm_trace_raw, dict) else None
                if isinstance(llm_request_trace, dict):
                    tracer.step(
                        "llm_request_payload",
                        provider=llm_request_trace.get("provider"),
                        protocol=llm_request_trace.get("protocol"),
                        model=llm_request_trace.get("model"),
                        max_tokens=llm_request_trace.get("max_tokens"),
                        prompt_length=llm_request_trace.get("prompt_length"),
                        prompt_preview=llm_request_trace.get("prompt_preview"),
                        prompt_preview_truncated=llm_request_trace.get("prompt_preview_truncated"),
                        system_message_length=llm_request_trace.get("system_message_length"),
                        system_message_preview=llm_request_trace.get("system_message_preview"),
                        system_message_preview_truncated=llm_request_trace.get("system_message_preview_truncated"),
                        chunking_enabled=llm_request_trace.get("chunking_enabled"),
                        context_window_tokens=llm_request_trace.get("context_window_tokens"),
                        reserve_tokens=llm_request_trace.get("reserve_tokens"),
                        input_safety_ratio=llm_request_trace.get("input_safety_ratio"),
                        input_budget_tokens=llm_request_trace.get("input_budget_tokens"),
                        total_estimated_input_tokens=llm_request_trace.get("total_estimated_input_tokens"),
                        estimated_map_request_count=llm_request_trace.get("estimated_map_request_count"),
                        actual_map_request_count=llm_request_trace.get("actual_map_request_count"),
                        reduce_request_count=llm_request_trace.get("reduce_request_count"),
                        total_request_count=llm_request_trace.get("total_request_count"),
                        overflow_file_count=llm_request_trace.get("overflow_file_count"),
                        overflow_files=llm_request_trace.get("overflow_files"),
                        chunk_plan=llm_request_trace.get("chunk_plan"),
                        map_calls=llm_request_trace.get("map_calls"),
                        reduce_call=llm_request_trace.get("reduce_call"),
                    )
                if isinstance(llm_response_trace, dict):
                    tracer.step(
                        "llm_response_payload",
                        protocol=llm_request_trace.get("protocol") if isinstance(llm_request_trace, dict) else None,
                        model=llm_response_trace.get("model"),
                        duration_ms=llm_response_trace.get("duration_ms"),
                        content_length=llm_response_trace.get("content_length"),
                        content_preview=llm_response_trace.get("content_preview"),
                        content_preview_truncated=llm_response_trace.get("content_preview_truncated"),
                        content_from_raw_fallback=llm_response_trace.get("content_from_raw_fallback"),
                        raw_response_length=llm_response_trace.get("raw_response_length"),
                        raw_response_preview=llm_response_trace.get("raw_response_preview"),
                        raw_response_preview_truncated=llm_response_trace.get("raw_response_preview_truncated"),
                        finish_reason=llm_response_trace.get("finish_reason"),
                        prompt_tokens=llm_response_trace.get("prompt_tokens"),
                        completion_tokens=llm_response_trace.get("completion_tokens"),
                        reasoning_tokens=llm_response_trace.get("reasoning_tokens"),
                        map_duration_ms_total=llm_response_trace.get("map_duration_ms_total"),
                        map_prompt_tokens_total=llm_response_trace.get("map_prompt_tokens_total"),
                        map_completion_tokens_total=llm_response_trace.get("map_completion_tokens_total"),
                        map_reasoning_tokens_total=llm_response_trace.get("map_reasoning_tokens_total"),
                        total_request_count=llm_response_trace.get("total_request_count"),
                        map_outputs=llm_response_trace.get("map_outputs"),
                        reduce_content=llm_response_trace.get("reduce_content"),
                    )
                elif llm_text:
                    tracer.step(
                        "llm_response_payload",
                        protocol="openai_compatible",
                        model=llm_model,
                        content_length=len(llm_text),
                        content_preview=llm_text,
                        content_preview_truncated=False,
                        content_from_raw_fallback=False,
                        raw_response_length=0,
                        raw_response_preview="",
                        raw_response_preview_truncated=False,
                        finish_reason="",
                        prompt_tokens=0,
                        completion_tokens=0,
                        reasoning_tokens=0,
                    )
                filter_summary_raw = review_result.get("filter_summary")
                if isinstance(filter_summary_raw, dict):
                    filter_summary = filter_summary_raw
                raw_files = review_result.get("files_reviewed")
                if isinstance(raw_files, list):
                    files_reviewed = [str(item) for item in raw_files if str(item)]
                    total_files = len(files_reviewed)

                if filter_summary:
                    excluded_sample = filter_summary.get("excluded_by_type_sample")
                    ignored_sample = filter_summary.get("ignored_by_pattern_sample")
                    tracer.step(
                        "changes_filtered",
                        raw_file_count=filter_summary.get("raw_file_count"),
                        filtered_file_count=filter_summary.get("filtered_file_count"),
                        removed_file_count=filter_summary.get("removed_file_count"),
                        excluded_by_type_count=filter_summary.get("excluded_by_type_count"),
                        ignored_by_pattern_count=filter_summary.get("ignored_by_pattern_count"),
                        deleted_file_count=filter_summary.get("deleted_file_count"),
                        renamed_without_diff_count=filter_summary.get("renamed_without_diff_count"),
                        excluded_by_type_sample=",".join([str(item) for item in excluded_sample[:5]]) if isinstance(excluded_sample, list) else "",
                        ignored_by_pattern_sample=",".join([str(item) for item in ignored_sample[:5]]) if isinstance(ignored_sample, list) else "",
                    )

            tracer.step(
                "review_result_ready",
                llm_model=llm_model,
                score=review_score,
                issues_count=len(review_issues) if isinstance(review_issues, list) else 0,
                highlights_count=len(review_highlights) if isinstance(review_highlights, list) else 0,
                summary_length=len(review_summary or ""),
                total_files=total_files,
                changes_count=changes_count,
                raw_file_count=filter_summary.get("raw_file_count") if filter_summary else None,
                filtered_file_count=filter_summary.get("filtered_file_count") if filter_summary else None,
                removed_file_count=filter_summary.get("removed_file_count") if filter_summary else None,
            )

            review_issues = normalize_issues(
                review_issues,
                default_owner_name=(author_name or None),
                default_owner_email=(author_email or None),
            )

            mr_info = {
                "project_id": project.project_id,
                "project_name": project.project_name,
                "title": mr_title,
                "author": author_name,
                "mr_iid": mr_iid,
                "url": mr_url,
                "description": mr_description,
                "source_branch": source_branch,
                "target_branch": target_branch,
                "file_count": total_files,
                "changes_count": changes_count,
                "object_attributes": attrs,
                "score": review_score,
                "summary": review_summary,
                "highlights": review_highlights,
                "issues": review_issues,
            }
            if provider.protocol == "mock":
                report_data = await report_generator.generate_mock(mr_info)
            else:
                report_data = await report_generator.generate(llm_text=llm_text, mr_info=mr_info, llm_model=llm_model)
            tracer.step(
                "report_generated",
                score=review_score,
                issues_count=len(review_issues) if isinstance(review_issues, list) else 0,
            )
            metadata = report_data.get("metadata") if isinstance(report_data, dict) else {}
            if isinstance(metadata, dict) and review_score is None:
                score_meta = metadata.get("score")
                if isinstance(score_meta, (int, float)):
                    review_score = int(score_meta)

            notification_result = await notifier.dispatch(report_data, mr_info, project.project_id, db)
            notification_items = notification_result.get("results")
            if isinstance(notification_items, list):
                for idx, raw_item in enumerate(notification_items):
                    if not isinstance(raw_item, dict):
                        continue
                    details = raw_item.get("details")
                    details_dict = details if isinstance(details, dict) else {}
                    message_preview, _ = _truncate_trace_text(raw_item.get("message"), limit=300)

                    request_payload = raw_item.get("request", details_dict.get("request"))
                    if (
                        raw_item.get("channel") == "gitlab"
                        and (request_payload is None or request_payload == {} or request_payload == "")
                    ):
                        project_id_value = _as_int(mr_info.get("project_id"))
                        mr_iid_value = _as_int(mr_info.get("mr_iid"))
                        endpoint = "/api/v4/projects/:project_id/merge_requests/:mr_iid/notes"
                        if project_id_value is not None and mr_iid_value is not None:
                            endpoint = f"/api/v4/projects/{project_id_value}/merge_requests/{mr_iid_value}/notes"
                        fallback_comment = notifier._gitlab_comment_message(report_data, mr_info)
                        request_payload = {
                            "project_id": project_id_value,
                            "mr_iid": mr_iid_value,
                            "method": "POST",
                            "endpoint": endpoint,
                            "body": {"body": fallback_comment},
                            "comment_length": len(fallback_comment),
                            "fallback": "queue_generated_request",
                        }
                    response_payload = raw_item.get("response", details_dict.get("response", details_dict))
                    status_code = details_dict.get("status_code")
                    if status_code is None and isinstance(response_payload, dict):
                        status_code = response_payload.get("status_code")
                    request_text, request_truncated = _serialize_trace_payload(request_payload)
                    response_text, response_truncated = _serialize_trace_payload(response_payload)

                    tracer.step(
                        _notification_channel_step_name(
                            channel_name=raw_item.get("channel_name"),
                            channel_type=raw_item.get("channel"),
                            index=idx,
                        ),
                        status="ok" if bool(raw_item.get("success")) else "warning",
                        channel=raw_item.get("channel"),
                        channel_name=raw_item.get("channel_name"),
                        success=bool(raw_item.get("success")),
                        result_message=message_preview,
                        response_time=raw_item.get("response_time"),
                        status_code=status_code,
                        request=request_text,
                        request_truncated=request_truncated,
                        response=response_text,
                        response_truncated=response_truncated,
                    )
            tracer.step(
                "notification_dispatched",
                success=bool(notification_result.get("success")),
                channels=notification_result.get("total_channels"),
                success_channels=notification_result.get("success_channels"),
                failed_channels=notification_result.get("failed_channels"),
            )
            channels_detail, channels_detail_truncated = _serialize_notification_results(notification_items)
            tracer.step(
                "notification_result_details",
                total_channels=notification_result.get("total_channels"),
                success_channels=notification_result.get("success_channels"),
                failed_channels=notification_result.get("failed_channels"),
                channels_detail=channels_detail,
                channels_detail_truncated=channels_detail_truncated,
            )
            review = await db.get(MergeRequestReview, review_id) if review_id is not None else None
            if review is not None:
                review.review_content = str(report_data.get("content") or llm_text)
                review.review_score = review_score
                review.review_issues = review_issues
                review.review_summary = review_summary
                review.review_highlights = review_highlights
                review.files_reviewed = files_reviewed
                review.total_files = total_files
                review.status = "completed"
                review.completed_at = datetime.now()
                review.error_message = None
                review.response_sent = bool(notification_result.get("success"))
                review.response_type = "notification"
                review.llm_provider = provider.name
                review.llm_model = llm_model
                review.is_mock = provider.protocol == "mock"
                review.notification_sent = bool(notification_result.get("success"))
                review.notification_result = notification_result
                await replace_review_findings(
                    db,
                    review=review,
                    issues=review_issues,
                )

            if webhook_log is not None:
                webhook_log.pipeline_trace = tracer.to_dict()
                webhook_log.processed = True
                webhook_log.processed_at = datetime.now()
                webhook_log.log_level = "INFO"
                webhook_log.skip_reason = None
                webhook_log.error_message = None

            await db.commit()
            return {
                "status": "completed",
                "project_id": project.project_id,
                "review_id": review_id,
                "webhook_log_id": tracked_webhook_log_id,
            }
    except Exception as exc:
        tracer.step(
            "pipeline_failed",
            status="error",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        logger.log_error_with_context(
            "review_merge_request_task_failed",
            error=exc,
            project_id=project_id,
            webhook_log_id=webhook_log_id,
            event_type=event_type,
        )
        async with session_factory() as db:
            if review_id is not None:
                review = await db.get(MergeRequestReview, review_id)
                if review is not None:
                    review.status = "failed"
                    review.error_message = str(exc)
                    review.completed_at = datetime.now()
            if tracked_webhook_log_id is not None:
                webhook_log = await db.get(WebhookLog, tracked_webhook_log_id)
                if webhook_log is not None:
                    webhook_log.pipeline_trace = tracer.to_dict()
                    webhook_log.log_level = "ERROR"
                    webhook_log.error_message = str(exc)
            await db.commit()

            # Send failure notification
            try:
                error_report = {
                    "content": (
                        f"# ❌ 代码审查失败\n\n"
                        f"- 项目: {project_id}\n"
                        f"- MR: !{mr_iid or 'N/A'} {mr_title}\n"
                        f"- 作者: {author_name}\n"
                        f"- 分支: {source_branch} → {target_branch}\n"
                        f"- 事件类型: {event_type}\n"
                        f"- 错误: {exc}\n"
                        f"- 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    ),
                    "metadata": {"is_error": True},
                }
                error_mr_info = {
                    "project_id": project_id,
                    "project_name": str(project_id),
                    "title": mr_title,
                    "author": author_name,
                    "mr_iid": mr_iid,
                    "url": mr_url,
                    "source_branch": source_branch,
                    "target_branch": target_branch,
                }
                project = await _find_project(db, project_id) if project_id else None
                if project is not None:
                    error_mr_info["project_name"] = project.project_name
                notifier = NotificationDispatcher(request_id=request_id)
                await notifier.dispatch(error_report, error_mr_info, project_id, db)
                logger.info("review_failure_notification_sent", project_id=project_id)
            except Exception as notify_exc:
                logger.warning("review_failure_notification_failed", error=str(notify_exc))
        raise
