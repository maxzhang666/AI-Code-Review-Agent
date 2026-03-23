from __future__ import annotations

import pytest

from app.models import NotificationChannel, Project, ProjectNotificationSetting


@pytest.mark.asyncio
async def test_list_notification_channels_excludes_gitlab(client, db_session) -> None:
    db_session.add_all(
        [
            NotificationChannel(
                name="DingTalk Main",
                notification_type="dingtalk",
                is_active=True,
                is_default=True,
                config_data={"webhook_url": "https://example.com/dingtalk"},
            ),
            NotificationChannel(
                name="Legacy GitLab",
                notification_type="gitlab",
                is_active=True,
                is_default=True,
                config_data={},
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/notification-channels/")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("count") == 1
    types = [item.get("notification_type") for item in payload.get("results", [])]
    assert "dingtalk" in types
    assert "gitlab" not in types


@pytest.mark.asyncio
async def test_create_notification_channel_rejects_gitlab_type(client) -> None:
    response = await client.post(
        "/api/notification-channels/",
        json={
            "name": "Legacy GitLab",
            "notification_type": "gitlab",
            "description": "should be rejected",
            "is_active": True,
            "is_default": False,
            "config_data": {},
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_project_notifications_hide_gitlab_channel_entries(client, db_session) -> None:
    project = Project(
        project_id=8001,
        project_name="notify-scope-demo",
        project_path="group/notify-scope-demo",
        project_url="https://gitlab.example.com/group/notify-scope-demo.git",
        namespace="group",
        review_enabled=True,
        gitlab_comment_notifications_enabled=True,
    )
    dingtalk_channel = NotificationChannel(
        name="DingTalk Main",
        notification_type="dingtalk",
        is_active=True,
        is_default=False,
        config_data={"webhook_url": "https://example.com/dingtalk"},
    )
    gitlab_channel = NotificationChannel(
        name="Legacy GitLab",
        notification_type="gitlab",
        is_active=True,
        is_default=False,
        config_data={},
    )
    db_session.add_all([project, dingtalk_channel, gitlab_channel])
    await db_session.flush()
    db_session.add_all(
        [
            ProjectNotificationSetting(project_id=project.id, channel_id=dingtalk_channel.id, enabled=True),
            ProjectNotificationSetting(project_id=project.id, channel_id=gitlab_channel.id, enabled=True),
        ]
    )
    await db_session.commit()

    response = await client.get(f"/api/webhook/projects/{project.project_id}/notifications/")
    assert response.status_code == 200
    payload = response.json()
    channels = payload.get("channels", [])
    assert len(channels) == 1
    assert channels[0].get("notification_type") == "dingtalk"
