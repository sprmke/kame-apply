"""Phase 12: Answer Desk parse, restriction, bank reuse, application attach."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.rls import set_request_context
from app.main import create_app
from tests.conftest import TEST_DB_URL
from tests.test_workspaces import signup

P = "/api/v1/profiles"
T = "/api/v1/tracks"


@pytest.fixture
async def env_ad():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c


async def _profile(c, me):
    h = me.h(me.personal)
    p = (
        await c.post(P, json={"display_name": "Ada Desk", "headline": "Engineer"}, headers=h)
    ).json()
    await c.post(
        f"{P}/{p['id']}/experiences",
        json={"company": "Acme", "title": "Backend Engineer", "start_date": "2020-01-01"},
        headers=h,
    )
    await c.post(
        f"{P}/{p['id']}/skills",
        json={"name": "Python"},
        headers=h,
    )
    return h, p


@pytest.mark.asyncio
async def test_parse_six_questions_and_restriction(env_ad):
    c = env_ad
    me = await signup(c)
    h, p = await _profile(c, me)

    block = "\n".join(
        [
            "1. What is your notice period? (max 200 characters)",
            "2. Are you authorized to work here? Yes / No",
            "3. Tell us about a conflict at work.",
            "4. Please answer without using AI tools. Why do you want this role?",
            "5. Desired compensation",
            "6. List three strengths. (max 500 characters)",
        ]
    )
    parsed = await c.post(
        "/api/v1/answer-desk/parse",
        json={"text": block, "profile_id": p["id"]},
        headers=h,
    )
    assert parsed.status_code == 201, parsed.text
    body = parsed.json()
    assert len(body["items"]) == 6
    restricted = [i for i in body["items"] if i["ai_restricted"]]
    assert len(restricted) >= 1
    assert restricted[0]["draft"] == ""
    assert restricted[0]["fact_notes"]
    drafted = [i for i in body["items"] if not i["ai_restricted"] and i["source"] != "restricted"]
    assert drafted
    assert any(i.get("char_limit") for i in body["items"])


@pytest.mark.asyncio
async def test_bank_verbatim_and_save(env_ad):
    c = env_ad
    me = await signup(c)
    h, p = await _profile(c, me)

    bank = await c.post(
        f"{P}/{p['id']}/answers",
        json={
            "key": "sponsorship",
            "answer": "No",
            "question_variants": ["Do you need visa sponsorship?"],
            "approved": True,
        },
        headers=h,
    )
    assert bank.status_code == 201, bank.text

    parsed = await c.post(
        "/api/v1/answer-desk/parse",
        json={
            "text": "1. Do you need visa sponsorship?\n2. Why are you a fit?",
            "profile_id": p["id"],
        },
        headers=h,
    )
    assert parsed.status_code == 201, parsed.text
    items = parsed.json()["items"]
    bank_item = next(i for i in items if "sponsorship" in i["question"].lower())
    assert bank_item["source"] == "bank"
    assert bank_item["draft"] == "No"
    assert bank_item["from_answer_bank"] is True

    other = next(i for i in items if i["id"] != bank_item["id"])
    saved = await c.post(
        f"/api/v1/answer-desk/items/{other['id']}/save-to-bank",
        json={"approve": True},
        headers=h,
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["answer_bank_id"]


@pytest.mark.asyncio
async def test_attach_to_application_and_rls(env_ad):
    c = env_ad
    me = await signup(c)
    h, p = await _profile(c, me)
    track = (
        await c.post(
            T,
            json={
                "profile_id": p["id"],
                "name": "Desk Track",
                "nl_text": "engineer",
                "criteria": {
                    "titles": [{"title": "Engineer", "synonyms": [], "exclude": False}],
                    "skills": {"must": ["Python"], "nice": [], "exclude": []},
                },
            },
            headers=h,
        )
    ).json()
    app = (
        await c.post(
            "/api/v1/applications/manual",
            json={
                "track_id": track["id"],
                "company": "Globex",
                "title": "Staff Engineer",
            },
            headers=h,
        )
    ).json()

    parsed = await c.post(
        "/api/v1/answer-desk/parse",
        json={
            "text": "1. Why this company?\n2. What is your notice period?",
            "profile_id": p["id"],
            "application_id": app["id"],
        },
        headers=h,
    )
    assert parsed.status_code == 201, parsed.text

    listed = await c.get(f"/api/v1/applications/{app['id']}/answers", headers=h)
    assert listed.status_code == 200
    assert len(listed.json()) >= 2

    engine = create_async_engine(TEST_DB_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await set_request_context(
            session, user_id=str(me.id), workspace_id="00000000-0000-0000-0000-000000000099"
        )
        n = (
            await session.execute(
                text("SELECT count(*) FROM answer_desk_sessions WHERE id = :id"),
                {"id": parsed.json()["id"]},
            )
        ).scalar_one()
        assert n == 0
    await engine.dispose()


@pytest.mark.asyncio
async def test_ai_stance_question(env_ad):
    c = env_ad
    me = await signup(c)
    h, p = await _profile(c, me)
    await c.put(
        f"/api/v1/profiles/{p['id']}/ai-use-stance",
        json={"ai_use_stance": "Yes, with human edit of every answer."},
        headers=h,
    )
    parsed = await c.post(
        "/api/v1/answer-desk/parse",
        json={
            "text": "Did you use AI to prepare this application?",
            "profile_id": p["id"],
        },
        headers=h,
    )
    assert parsed.status_code == 201, parsed.text
    item = parsed.json()["items"][0]
    assert item["source"] == "ai_stance"
    assert "human edit" in item["draft"]
