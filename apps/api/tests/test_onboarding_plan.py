"""Onboarding plan: rule-based resume reading and the read-only bundle."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app
from app.onboarding.parse import parse_resume_text
from tests.conftest import TEST_DB_URL
from tests.test_workspaces import signup

RESUME = """ANA REYES
Customer Support Lead
Manila, Philippines
ana.reyes@example.com

Skills: onboarding, Zendesk, team leadership, QA

Experience
2020 - 2025 Support Lead at Acme
"""


def test_parse_resume_reads_basics_without_ai():
    out = parse_resume_text(RESUME)
    assert out["name"] == "ANA REYES" or out["name"] == "Ana Reyes"
    assert out["email"] == "ana.reyes@example.com"
    assert out["headline"] == "Customer Support Lead"
    assert out["location"] == "Manila, Philippines"
    assert "Zendesk" in out["skills"]
    assert out["years"] and out["years"] >= 1


def test_parse_resume_never_returns_sensitive_values():
    out = parse_resume_text("Ana Reyes\nSSN 123-45-6789\nana@example.com\n")
    assert "123-45-6789" not in str(out)


@pytest.fixture
async def env():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://o"
        ) as client:
            yield client


async def test_plan_returns_basics_search_and_schedule(env):
    me = await signup(env)
    r = await env.post(
        "/api/v1/onboarding/plan",
        json={
            "resume_text": RESUME,
            "role_text": "customer support lead, remote",
            "timezone": "Asia/Manila",
        },
        headers=me.h(me.personal),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["basics"]["email"] == "ana.reyes@example.com"
    assert body["search"]["criteria"]["titles"]
    assert body["search"]["source"] in {"defaults", "ai"}
    assert body["schedule"]["preset"] == "every_4_hours"
    assert body["schedule"]["timezone"] == "Asia/Manila"


async def test_plan_without_input_is_empty_not_invented(env):
    me = await signup(env)
    r = await env.post("/api/v1/onboarding/plan", json={}, headers=me.h(me.personal))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["basics"]["name"] == ""
    assert body["search"] is None
    assert body["answers"] == []
