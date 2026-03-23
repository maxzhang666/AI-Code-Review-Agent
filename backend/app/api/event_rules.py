from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.deps import get_db, get_request_id
from app.core.logging import get_logger
from app.models import Project, ProjectWebhookEventPrompt, WebhookEventRule
from app.schemas.event_rule import WebhookEventRuleCreate, WebhookEventRuleResponse, WebhookEventRuleUpdate

router = APIRouter()


async def _get_rule_or_404(rule_id: int, db: AsyncSession) -> WebhookEventRule:
    rule = await db.get(WebhookEventRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Webhook event rule not found.")
    return rule


@router.get("/webhook-event-rules/")
async def list_webhook_event_rules(
    page: int = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    settings = get_settings()
    page_size = settings.PAGE_SIZE
    offset = (page - 1) * page_size

    count = len((await db.execute(select(WebhookEventRule.id))).all())
    rules = (
        await db.execute(
            select(WebhookEventRule)
            .order_by(WebhookEventRule.created_at.desc(), WebhookEventRule.id.desc())
            .offset(offset)
            .limit(page_size)
        )
    ).scalars().all()

    return {
        "count": count,
        "results": [WebhookEventRuleResponse.model_validate(rule, from_attributes=True) for rule in rules],
    }


@router.post("/webhook-event-rules/", response_model=WebhookEventRuleResponse)
async def create_webhook_event_rule(
    payload: WebhookEventRuleCreate,
    db: AsyncSession = Depends(get_db),
) -> WebhookEventRuleResponse:
    rule = WebhookEventRule(
        name=payload.name,
        event_type=payload.event_type,
        description=payload.description,
        match_rules=payload.match_rules,
        is_active=payload.is_active,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return WebhookEventRuleResponse.model_validate(rule, from_attributes=True)


@router.get("/webhook-event-rules/{rule_id}/", response_model=WebhookEventRuleResponse)
async def get_webhook_event_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
) -> WebhookEventRuleResponse:
    rule = await _get_rule_or_404(rule_id, db)
    return WebhookEventRuleResponse.model_validate(rule, from_attributes=True)


@router.patch("/webhook-event-rules/{rule_id}/", response_model=WebhookEventRuleResponse)
async def patch_webhook_event_rule(
    rule_id: int,
    payload: WebhookEventRuleUpdate,
    db: AsyncSession = Depends(get_db),
) -> WebhookEventRuleResponse:
    rule = await _get_rule_or_404(rule_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    await db.commit()
    await db.refresh(rule)
    return WebhookEventRuleResponse.model_validate(rule, from_attributes=True)


@router.delete("/webhook-event-rules/{rule_id}/")
async def delete_webhook_event_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    rule = await _get_rule_or_404(rule_id, db)
    await db.delete(rule)
    await db.commit()
    return {"code": 200, "message": "Webhook event rule deleted"}


@router.post("/webhook-event-rules/{rule_id}/test_rule/")
async def test_webhook_event_rule(
    rule_id: int,
    body: dict[str, Any] = Body(default_factory=dict),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    rule = await _get_rule_or_404(rule_id, db)
    payload = body.get("payload")
    payload_dict = payload if isinstance(payload, dict) else {}
    return {
        "rule_id": rule.id,
        "matches": rule.matches_payload(payload_dict),
        "payload": payload_dict,
    }


@router.get("/webhook-event-rules/{rule_id}/usage/")
async def get_webhook_event_rule_usage(
    rule_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    rule = await _get_rule_or_404(rule_id, db)

    prompts_count = len(
        (
            await db.execute(
                select(ProjectWebhookEventPrompt.id).where(ProjectWebhookEventPrompt.event_rule_id == rule_id)
            )
        ).all()
    )

    project_rows = (
        await db.execute(select(Project.project_id, Project.enabled_webhook_events))
    ).all()
    enabled_count = 0
    for _, enabled_events in project_rows:
        if isinstance(enabled_events, list) and rule_id in enabled_events:
            enabled_count += 1

    return {
        "rule_id": rule.id,
        "prompt_bindings": prompts_count,
        "projects_with_rule_enabled": enabled_count,
    }


@router.post("/webhook-event-rules/validate_payload/")
async def validate_webhook_event_payload(
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    rule_data = body.get("rule")
    payload = body.get("payload")

    if not isinstance(rule_data, dict):
        raise HTTPException(status_code=400, detail="Field 'rule' must be an object.")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Field 'payload' must be an object.")

    match_rules = rule_data.get("match_rules", {})
    probe = WebhookEventRule(
        name=str(rule_data.get("name") or "probe"),
        event_type=str(rule_data.get("event_type") or "probe"),
        description=str(rule_data.get("description") or ""),
        match_rules=match_rules,
        is_active=True,
    )
    return {"valid": True, "matches": probe.matches_payload(payload)}


@router.post("/webhook-event-rules/initialize_defaults/")
async def initialize_default_webhook_event_rules(
    db: AsyncSession = Depends(get_db),
    request_id: str | None = Depends(get_request_id),
) -> dict[str, Any]:
    logger = get_logger(__name__, request_id)
    defaults = [
        {
            "name": "Merge Request Opened",
            "event_type": "Merge Request Hook",
            "description": "Triggered when merge request is opened or updated",
            "match_rules": {"object_attributes": {"action": "open"}},
        },
        {
            "name": "Merge Request Updated",
            "event_type": "Merge Request Hook",
            "description": "Triggered when merge request is updated",
            "match_rules": {"object_attributes": {"action": "update"}},
        },
        {
            "name": "Merge Request Approved",
            "event_type": "Merge Request Hook",
            "description": "Triggered when merge request is approved",
            "match_rules": {"object_attributes": {"action": "approved"}},
        },
        {
            "name": "Push Event",
            "event_type": "Push Hook",
            "description": "Triggered on push event",
            "match_rules": {},
        },
    ]

    created = 0
    for item in defaults:
        exists = (
            await db.execute(
                select(WebhookEventRule)
                .where(
                    WebhookEventRule.name == item["name"],
                    WebhookEventRule.event_type == item["event_type"],
                )
                .limit(1)
            )
        ).scalars().first()
        if exists:
            continue
        db.add(
            WebhookEventRule(
                name=item["name"],
                event_type=item["event_type"],
                description=item["description"],
                match_rules=item["match_rules"],
                is_active=True,
            )
        )
        created += 1

    await db.commit()
    logger.info("webhook_event_defaults_initialized", created=created)
    return {"code": 200, "message": "Default webhook event rules initialized", "created": created}
