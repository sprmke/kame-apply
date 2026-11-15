"""Reply auto-match: no application ids, workspace scoped (A5)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app
from tests.conftest import TEST_DB_URL
from tests.test_workspaces import signup

P = "/api/v1/profiles"
T = "/api/v1/tracks"
A = "/api/v1/applications"


@pytest.fixture
async def env():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://r"
        ) as client:
            yield client


async def _application(c, who, *, company: str, title: str):
    profile = (
        await c.post(P, json={"display_name": "Ana Reyes"}, headers=who.h(who.personal))
    ).json()
    track = (
        await c.post(
            T,
            json={"profile_id": profile["id"], "name": "Support", "nl_text": "support lead"},
            headers=who.h(who.personal),
        )
    ).json()
    app = (
        await c.post(
            A + "/manual",
            json={"track_id": track["id"], "company": company, "title": title},
            headers=who.h(who.personal),
        )
    ).json()
    return app


async def test_matches_by_company_and_sender(env):
    me = await signup(env)
    app = await _application(env, me, company="Acme Support", title="Support Lead")
    r = await env.post(
        "/api/v1/responses/match",
        json={
            "sender": "recruiter@acmesupport.com",
            "subject": "Your application",
            "body_text": "Thanks for applying to the Support Lead role at Acme Support.",
        },
        headers=me.h(me.personal),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["application_id"] == app["id"]
    assert body["score"] > 0


async def test_no_match_is_null(env):
    me = await signup(env)
    await _application(env, me, company="Acme Support", title="Support Lead")
    r = await env.post(
        "/api/v1/responses/match",
        json={"sender": "hello@elsewhere.com", "subject": "Hi", "body_text": "Unrelated note."},
        headers=me.h(me.personal),
    )
    assert r.status_code == 200, r.text
    assert r.json() is None


async def test_never_matches_another_workspace(env):
    me = await signup(env)
    other = await signup(env)
    await _application(env, other, company="Globex", title="Designer")
    r = await env.post(
        "/api/v1/responses/match",
        json={
            "sender": "jobs@globex.com",
            "subject": "Designer",
            "body_text": "Your Globex Designer application",
        },
        headers=me.h(me.personal),
    )
    assert r.json() is None
