from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from app.models import LLMProvider, Project


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
