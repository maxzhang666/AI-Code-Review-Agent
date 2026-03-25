from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_weekly_reports_are_public_for_anonymous_client(anonymous_client) -> None:
    team_response = await anonymous_client.get("/api/webhook/reports/mr-feedback/weekly/")
    assert team_response.status_code == 200
    team_payload = team_response.json()
    assert "summary" in team_payload

    member_response = await anonymous_client.get("/api/webhook/reports/developers/weekly/")
    assert member_response.status_code == 200
    member_payload = member_response.json()
    assert "summary" in member_payload

    card_response = await anonymous_client.get("/api/webhook/reports/developers/weekly/cards/")
    assert card_response.status_code == 200
    card_payload = card_response.json()
    assert "results" in card_payload
