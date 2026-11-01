"""Phase 8 API: create, critique, improve, render, insights, RLS."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.rls import set_request_context
from app.jobs.models import Job, TrackJob
from app.main import create_app
from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_workspaces import signup

P = "/api/v1/profiles"
T = "/api/v1/tracks"
R = "/api/v1/resumes"


@pytest.fixture
async def env_r():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c


async def _seed_profile_track(c, me):
    h = me.h(me.personal)
    p = (
        await c.post(P, json={"display_name": "Ada Lovelace", "headline": "Engineer"}, headers=h)
    ).json()
    await c.patch(f"{P}/{p['id']}", json={"summary": "Builds analytical engines"}, headers=h)
    exp = (
        await c.post(
            f"{P}/{p['id']}/experiences",
            json={
                "company": "Analytical Engines",
                "title": "Engineer",
                "start_date": "1840-01-01",
                "is_current": True,
            },
            headers=h,
        )
    ).json()
    await c.post(
        f"{P}/{p['id']}/bullets",
        json={"experience_id": exp["id"], "text": "Wrote algorithms for 12 clients"},
        headers=h,
    )
    await c.post(f"{P}/{p['id']}/skills", json={"name": "Mathematics"}, headers=h)
    await c.post(f"{P}/{p['id']}/skills", json={"name": "Python"}, headers=h)
    track = (
        await c.post(
            T,
            json={
                "profile_id": p["id"],
                "name": "Engineer roles",
                "criteria": {
                    "titles": [{"title": "Engineer", "synonyms": [], "exclude": False}],
                    "skills": {"must": ["Python"], "nice": ["Mathematics"], "exclude": []},
                },
            },
            headers=h,
        )
    ).json()
    return p, track, h


async def _seed_matched_jobs(me, track_id: str, n: int = 5) -> None:
    engine = create_async_engine(TEST_OWNER_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await set_request_context(session, user_id=str(me.id), workspace_id=str(me.personal))
        for i in range(n):
            job = Job(
                title="Software Engineer",
                normalized_title="software engineer",
                description_text="Python Mathematics SQL required",
                description_html="<p>Python</p>",
                content_hash=f"resume-job-{uuid.uuid4().hex}",
                simhash=i + 100,
                canonical_url=f"https://example.com/jobs/{uuid.uuid4().hex}",
                apply_url=f"https://example.com/apply/{uuid.uuid4().hex}",
                status="open",
                skills=["Python", "Mathematics", "SQL"],
                salary={"min": 90000, "max": 140000, "currency": "USD"},
            )
            session.add(job)
            await session.flush()
            session.add(
                TrackJob(
                    workspace_id=uuid.UUID(str(me.personal)),
                    track_id=uuid.UUID(track_id),
                    job_id=job.id,
                    eligibility="eligible",
                    status="new",
                )
            )
        await session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_critique_improve_render_flow(env_r):
    c = env_r
    me = await signup(c)
    p, track, h = await _seed_profile_track(c, me)

    created = await c.post(
        R,
        json={"profile_id": p["id"], "track_id": track["id"], "label": "Engineer base"},
        headers=h,
    )
    assert created.status_code == 201, created.text
    ver = created.json()
    assert ver["content"]["contact"]["full_name"] == "Ada Lovelace"
    assert ver["content"].get("summary") or ver["content"].get("sections")

    critique = await c.post(f"{R}/{ver['id']}/critique", headers=h)
    assert critique.status_code == 200, critique.text
    body = critique.json()
    assert "categories" in body and "top_fixes" in body
    assert "skim_zone" in body

    await _seed_matched_jobs(me, track["id"], n=8)
    insights = await c.post(f"/api/v1/tracks/{track['id']}/insights?window_days=30", headers=h)
    assert insights.status_code == 200, insights.text
    ins = insights.json()
    assert ins["sample_size"] >= 5
    assert ins["low_confidence"] is True  # < 30
    assert isinstance(ins["skills"], list)

    improve = await c.post(f"{R}/{ver['id']}/improve", json={"window_days": 30}, headers=h)
    assert improve.status_code == 200, improve.text
    changes = improve.json()
    assert isinstance(changes, list)

    if changes:
        ch = changes[0]
        if ch["op"] != "ask_metric":
            d = await c.post(
                f"/api/v1/resume-changes/{ch['id']}",
                json={"status": "accepted"},
                headers=h,
            )
            assert d.status_code == 200, d.text
            applied = await c.post(f"{R}/{ver['id']}/apply", headers=h)
            assert applied.status_code == 200, applied.text

    rendered = await c.post(
        f"{R}/{ver['id']}/render",
        json={"template": "classic", "page_size": "letter"},
        headers=h,
    )
    assert rendered.status_code == 200, rendered.text
    out = rendered.json()
    assert out["parse_gate"]["ok"] is True
    assert out["docx_url"] or out["engine"]

    broken = await c.post(
        f"{R}/{ver['id']}/render",
        json={"broken": True},
        headers=h,
    )
    assert broken.status_code == 200, broken.text
    assert broken.json()["parse_gate"]["ok"] is False

    parse = await c.get(f"{R}/{ver['id']}/parse-view", headers=h)
    assert parse.status_code == 200
    assert parse.json()["name"]


@pytest.mark.asyncio
async def test_resume_cross_tenant_isolation(env_r):
    c = env_r
    a = await signup(c)
    b = await signup(c)
    p, track, ah = await _seed_profile_track(c, a)
    created = await c.post(
        R,
        json={"profile_id": p["id"], "track_id": track["id"]},
        headers=ah,
    )
    assert created.status_code == 201
    vid = created.json()["id"]

    bh = b.h(b.personal)
    assert (await c.get(f"{R}/{vid}", headers=bh)).status_code == 404
    assert (await c.post(f"{R}/{vid}/critique", headers=bh)).status_code == 404
    listed = await c.get(R, headers=bh)
    assert listed.status_code == 200
    assert listed.json() == []


@pytest.mark.asyncio
async def test_rls_wrong_workspace_zero_rows(env_r):
    c = env_r
    me = await signup(c)
    p, track, h = await _seed_profile_track(c, me)
    created = await c.post(R, json={"profile_id": p["id"], "track_id": track["id"]}, headers=h)
    assert created.status_code == 201
    from sqlalchemy import text

    engine = create_async_engine(TEST_OWNER_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(text("SET ROLE kame_apply_app"))
        await set_request_context(session, user_id=str(me.id), workspace_id=str(uuid.uuid4()))
        n = (await session.execute(text("SELECT count(*) FROM resume_versions"))).scalar_one()
        assert int(n) == 0
        n2 = (await session.execute(text("SELECT count(*) FROM market_insights"))).scalar_one()
        assert int(n2) == 0
        n3 = (await session.execute(text("SELECT count(*) FROM resume_changes"))).scalar_one()
        assert int(n3) == 0
        await session.execute(text("RESET ROLE"))
    await engine.dispose()
