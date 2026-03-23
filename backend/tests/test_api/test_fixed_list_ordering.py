from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from app.models import GitLabConfig, LLMProvider, NotificationChannel, Project, WebhookEventRule


@pytest.mark.asyncio
async def test_llm_list_order_is_stable_after_updates(client, db_session) -> None:
    create_payload_a = {
        "name": "provider-a",
        "protocol": "openai_compatible",
        "is_active": True,
        "is_default": False,
        "config_data": {"model": "gpt-a"},
    }
    create_payload_b = {
        "name": "provider-b",
        "protocol": "openai_compatible",
        "is_active": True,
        "is_default": False,
        "config_data": {"model": "gpt-b"},
    }

    create_a_resp = await client.post("/api/llm-configs/", json=create_payload_a)
    create_b_resp = await client.post("/api/llm-configs/", json=create_payload_b)
    assert create_a_resp.status_code == 200
    assert create_b_resp.status_code == 200

    provider_a_id = int(create_a_resp.json()["id"])
    provider_b_id = int(create_b_resp.json()["id"])

    provider_a = (
        await db_session.execute(select(LLMProvider).where(LLMProvider.id == provider_a_id))
    ).scalars().one()
    provider_b = (
        await db_session.execute(select(LLMProvider).where(LLMProvider.id == provider_b_id))
    ).scalars().one()

    provider_a.created_at = datetime(2026, 1, 1, 9, 0, 0)
    provider_a.updated_at = datetime(2026, 1, 1, 9, 0, 0)
    provider_b.created_at = datetime(2026, 1, 2, 9, 0, 0)
    provider_b.updated_at = datetime(2026, 1, 2, 9, 0, 0)
    await db_session.commit()

    # Simulate updating an older record so updated_at becomes newer.
    provider_a.name = "provider-a-updated"
    provider_a.updated_at = datetime(2026, 2, 1, 9, 0, 0)
    await db_session.commit()

    response = await client.get("/api/llm-configs/")
    assert response.status_code == 200
    payload = response.json()
    ids = [int(item["id"]) for item in payload["results"]]
    assert ids == [provider_b_id, provider_a_id]


@pytest.mark.asyncio
async def test_project_list_order_is_stable_after_updates(client, db_session) -> None:
    project_a = Project(
        project_id=12001,
        project_name="project-a",
        project_path="group/project-a",
        project_url="https://gitlab.example.com/group/project-a.git",
        namespace="group",
        review_enabled=True,
        gitlab_data={},
        created_at=datetime(2026, 1, 1, 9, 0, 0),
        updated_at=datetime(2026, 1, 1, 9, 0, 0),
    )
    project_b = Project(
        project_id=12002,
        project_name="project-b",
        project_path="group/project-b",
        project_url="https://gitlab.example.com/group/project-b.git",
        namespace="group",
        review_enabled=True,
        gitlab_data={},
        created_at=datetime(2026, 1, 2, 9, 0, 0),
        updated_at=datetime(2026, 1, 2, 9, 0, 0),
    )
    db_session.add_all([project_a, project_b])
    await db_session.commit()

    # Simulate updating an older record so updated_at becomes newer.
    project_a.project_name = "project-a-updated"
    project_a.updated_at = datetime(2026, 2, 1, 9, 0, 0)
    await db_session.commit()

    response = await client.get("/api/webhook/projects/")
    assert response.status_code == 200
    payload = response.json()
    project_ids = [int(item["project_id"]) for item in payload["results"]]
    assert project_ids == [project_b.project_id, project_a.project_id]


@pytest.mark.asyncio
async def test_webhook_event_rule_list_order_is_stable_after_updates(client, db_session) -> None:
    rule_a = WebhookEventRule(
        name="rule-a",
        event_type="Push Hook",
        description="A",
        match_rules={},
        is_active=True,
        created_at=datetime(2026, 1, 1, 9, 0, 0),
        updated_at=datetime(2026, 1, 1, 9, 0, 0),
    )
    rule_b = WebhookEventRule(
        name="rule-b",
        event_type="Merge Request Hook",
        description="B",
        match_rules={},
        is_active=True,
        created_at=datetime(2026, 1, 2, 9, 0, 0),
        updated_at=datetime(2026, 1, 2, 9, 0, 0),
    )
    db_session.add_all([rule_a, rule_b])
    await db_session.commit()

    # Simulate updating an older record so updated_at becomes newer.
    rule_a.name = "rule-a-updated"
    rule_a.updated_at = datetime(2026, 2, 1, 9, 0, 0)
    await db_session.commit()

    response = await client.get("/api/webhook-event-rules/")
    assert response.status_code == 200
    payload = response.json()
    ids = [int(item["id"]) for item in payload["results"]]
    assert ids == [rule_b.id, rule_a.id]


@pytest.mark.asyncio
async def test_notification_channel_list_order_is_stable_after_updates(client, db_session) -> None:
    channel_a = NotificationChannel(
        name="channel-a",
        notification_type="dingtalk",
        description="A",
        is_active=True,
        is_default=False,
        config_data={"webhook_url": "https://example.com/a"},
        created_at=datetime(2026, 1, 1, 9, 0, 0),
        updated_at=datetime(2026, 1, 1, 9, 0, 0),
    )
    channel_b = NotificationChannel(
        name="channel-b",
        notification_type="slack",
        description="B",
        is_active=True,
        is_default=False,
        config_data={"webhook_url": "https://example.com/b"},
        created_at=datetime(2026, 1, 2, 9, 0, 0),
        updated_at=datetime(2026, 1, 2, 9, 0, 0),
    )
    db_session.add_all([channel_a, channel_b])
    await db_session.commit()

    # Simulate updating an older record so updated_at becomes newer.
    channel_a.description = "A-updated"
    channel_a.updated_at = datetime(2026, 2, 1, 9, 0, 0)
    await db_session.commit()

    response = await client.get("/api/notification-channels/")
    assert response.status_code == 200
    payload = response.json()
    ids = [int(item["id"]) for item in payload["results"]]
    assert ids == [channel_b.id, channel_a.id]


@pytest.mark.asyncio
async def test_gitlab_config_list_order_is_stable_after_updates(client, db_session) -> None:
    config_a = GitLabConfig(
        server_url="https://gitlab-a.example.com",
        private_token="token-a",
        site_url="https://site-a.example.com",
        is_active=True,
        created_at=datetime(2026, 1, 1, 9, 0, 0),
        updated_at=datetime(2026, 1, 1, 9, 0, 0),
    )
    config_b = GitLabConfig(
        server_url="https://gitlab-b.example.com",
        private_token="token-b",
        site_url="https://site-b.example.com",
        is_active=True,
        created_at=datetime(2026, 1, 2, 9, 0, 0),
        updated_at=datetime(2026, 1, 2, 9, 0, 0),
    )
    db_session.add_all([config_a, config_b])
    await db_session.commit()

    # Simulate updating an older record so updated_at becomes newer.
    config_a.site_url = "https://site-a-updated.example.com"
    config_a.updated_at = datetime(2026, 2, 1, 9, 0, 0)
    await db_session.commit()

    response = await client.get("/api/gitlab-configs/")
    assert response.status_code == 200
    payload = response.json()
    ids = [int(item["id"]) for item in payload["results"]]
    assert ids == [config_b.id, config_a.id]
