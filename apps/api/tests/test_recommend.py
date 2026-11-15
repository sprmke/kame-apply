"""Recommended settings and voice presets."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app
from app.notifications.service import default_enabled
from tests.conftest import TEST_DB_URL
from tests.test_workspaces import signup

P = "/api/v1/profiles"
T = "/api/v1/tracks"


@pytest.fixture
async def env():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://s"
        ) as client:
            yield client


async def test_recommendation_works_without_history(env):
    me = await signup(env)
    profile = (
        await env.post(P, json={"display_name": "Ana Reyes"}, headers=me.h(me.personal))
    ).json()
    track = (
        await env.post(
            T,
            json={"profile_id": profile["id"], "name": "Support", "nl_text": "support lead"},
            headers=me.h(me.personal),
        )
    ).json()
    r = await env.get(f"{T}/{track['id']}/recommended-settings", headers=me.h(me.personal))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["autonomy"] in {"discover", "prepare"}
    assert body["preset"] in {"every_4_hours", "every_2_hours", "daily_morning"}
    assert body["minimum_match"] == 85
    assert body["reasons"]


async def test_voice_preset_applies_without_samples(env):
    me = await signup(env)
    profile = (
        await env.post(P, json={"display_name": "Ana Reyes"}, headers=me.h(me.personal))
    ).json()
    r = await env.post(
        f"{P}/{profile['id']}/voice/preset",
        json={"preset": "warm"},
        headers=me.h(me.personal),
    )
    assert r.status_code == 200, r.text
    style = r.json()["style"]
    assert style["summary"].startswith("Warm")
    assert style["preset"] == "warm"


def test_notification_defaults_are_quiet():
    assert default_enabled("in_app", "strong_match") is True
    assert default_enabled("email", "digest") is True
    assert default_enabled("email", "needs_review") is True
    assert default_enabled("email", "run_failed") is False
    assert default_enabled("email", "strong_match") is False
