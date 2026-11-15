"""Answer-bank drafts from profile facts (A3)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app
from tests.conftest import TEST_DB_URL
from tests.test_workspaces import signup

P = "/api/v1/profiles"


@pytest.fixture
async def env():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://a"
        ) as client:
            yield client


async def _profile(c, who, **extra):
    links = extra.pop("links", None)
    body = {"display_name": "Ana Reyes"}
    r = await c.post(P, json=body, headers=who.h(who.personal))
    assert r.status_code == 201, r.text
    profile = r.json()
    patch = {**extra}
    if links is not None:
        patch["links"] = links
    if patch:
        updated = await c.patch(f"{P}/{profile['id']}", json=patch, headers=who.h(who.personal))
        assert updated.status_code == 200, updated.text
        profile = updated.json()
    return profile


async def test_drafts_from_profile_facts(env):
    me = await signup(env)
    profile = await _profile(
        env,
        me,
        work_authorization={"countries": ["PH"], "authorized": True, "needs_sponsorship": False},
        salary_prefs={"floor": 60000, "currency": "PHP", "period": "month"},
        links=[{"label": "LinkedIn", "url": "https://linkedin.com/in/ana"}],
    )
    r = await env.post(
        f"{P}/{profile['id']}/answers/draft",
        json={},
        headers=me.h(me.personal),
    )
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    by_key = {item["key"] + ":" + str(item["country"]): item for item in items}
    assert by_key["work_authorization:PH"]["draft"] == "Yes"
    assert by_key["sponsorship:None"]["draft"] == "No"
    assert "60,000" in by_key["salary_expectation:None"]["draft"]
    assert by_key["linkedin_url:None"]["draft"] == "https://linkedin.com/in/ana"
    assert by_key["eeo_gender:None"]["draft"] == "Decline to self-identify"
    assert by_key["work_authorization:PH"]["source"] == "profile"


async def test_drafts_skip_existing_and_never_guess_eligibility(env):
    me = await signup(env)
    profile = await _profile(env, me, work_authorization={"countries": ["PH"]})
    r = await env.post(
        f"{P}/{profile['id']}/answers/draft",
        json={"keys": ["work_authorization"]},
        headers=me.h(me.personal),
    )
    assert r.status_code == 200, r.text
    item = r.json()["items"][0]
    assert item["source"] == "needs_story"
    assert item["draft"] == ""

    created = await env.post(
        f"{P}/{profile['id']}/answers",
        json={"key": "work_authorization", "country": "PH", "answer": "Yes", "approved": True},
        headers=me.h(me.personal),
    )
    assert created.status_code == 201, created.text

    again = await env.post(
        f"{P}/{profile['id']}/answers/draft",
        json={"keys": ["work_authorization"]},
        headers=me.h(me.personal),
    )
    assert again.json()["items"] == []
