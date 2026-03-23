from __future__ import annotations

from typing import Any, Callable

from app.services.notification.channels import NotificationResult, truncate_text


def is_trace_payload_empty(payload: Any) -> bool:
    return payload is None or payload == {} or payload == ""


def build_gitlab_request_payload(
    project_id: int | None,
    mr_iid: int | None,
    comment: str,
) -> dict[str, Any]:
    endpoint = "/api/v4/projects/:project_id/merge_requests/:mr_iid/notes"
    if project_id is not None and mr_iid is not None:
        endpoint = f"/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
    return {
        "project_id": project_id,
        "mr_iid": mr_iid,
        "method": "POST",
        "endpoint": endpoint,
        "body": {"body": comment},
        "comment_length": len(comment),
        "comment_preview": truncate_text(comment, 800),
    }


def build_gitlab_response_payload(result: Any) -> dict[str, Any]:
    payload = result if isinstance(result, dict) else {}
    note_id = payload.get("id")
    if note_id is None:
        note_id = payload.get("note_id")
    return {
        "note_id": note_id,
        "body": payload,
    }


def normalize_result_fields(
    raw_result: NotificationResult,
    details: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any]]:
    request_payload = details.get("request")
    response_payload = details.get("response")
    status_code = details.get("status_code")
    if status_code is None and isinstance(response_payload, dict):
        status_code = response_payload.get("status_code")

    trace = {
        "request": request_payload if isinstance(request_payload, dict) else {},
        "response": response_payload if isinstance(response_payload, dict) else {},
    }

    error: dict[str, Any] | None = None
    if not bool(raw_result.get("success", False)):
        error = {
            "code": "channel_send_failed",
            "message": str(raw_result.get("message") or ""),
        }
        if status_code is not None:
            error["status_code"] = status_code

    meta: dict[str, Any] = {}
    if status_code is not None:
        meta["status_code"] = status_code
    note_id = details.get("note_id")
    if note_id is not None:
        meta["note_id"] = note_id

    return trace, error, meta


def normalize_trace_details(
    channel_type: str,
    details: dict[str, Any],
    report_data: dict[str, Any],
    mr_info: dict[str, Any],
    *,
    extract_project_id: Callable[[dict[str, Any]], int | None],
    extract_mr_iid: Callable[[dict[str, Any]], int | None],
    build_comment_message: Callable[[dict[str, Any], dict[str, Any]], str],
) -> dict[str, Any]:
    normalized = dict(details)
    if channel_type != "gitlab":
        return normalized

    request_payload = normalized.get("request")
    if is_trace_payload_empty(request_payload):
        project_id = extract_project_id(mr_info)
        mr_iid = extract_mr_iid(mr_info)
        comment = build_comment_message(report_data, mr_info)
        request_payload = build_gitlab_request_payload(
            project_id=project_id,
            mr_iid=mr_iid,
            comment=comment,
        )
        if isinstance(request_payload, dict):
            request_payload["fallback"] = "dispatcher_generated_request"

    response_payload = normalized.get("response")
    if is_trace_payload_empty(response_payload):
        response_payload = build_gitlab_response_payload(normalized)
        if is_trace_payload_empty(response_payload.get("body")):
            response_payload["fallback"] = "dispatcher_generated_response"

    normalized["request"] = request_payload
    normalized["response"] = response_payload
    return normalized
