"""Phase 9 API: tailor → accept → application; RLS; re-tailor versions."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.rls import set_request_context
from app.jobs.models import Job, TrackJob
from app.main import create_app
from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_workspaces import signup

P = "/api/v1/profiles"
T = "/api/v1/tracks"


@pytest.fixture
async def env_t():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c


async def _seed(c, me):
    h = me.h(me.personal)
    p = (
        await c.post(
            P,
            json={"display_name": "Ada Lovelace", "headline": "Backend Engineer"},
            headers=h,
        )
    ).json()
    await c.patch(f"{P}/{p['id']}", json={"summary": "Builds APIs"}, headers=h)
    exp = (
        await c.post(
            f"{P}/{p['id']}/experiences",
            json={
                "company": "Acme",
                "title": "Engineer",
                "start_date": "2019-01-01",
                "is_current": True,
            },
            headers=h,
        )
    ).json()
    await c.post(
        f"{P}/{p['id']}/bullets",
        json={"experience_id": exp["id"], "text": "Built FastAPI services for 12 teams"},
        headers=h,
    )
    await c.post(f"{P}/{p['id']}/skills", json={"name": "Python"}, headers=h)
    await c.post(f"{P}/{p['id']}/skills", json={"name": "FastAPI"}, headers=h)
    await c.post(f"{P}/{p['id']}/skills", json={"name": "PostgreSQL"}, headers=h)
    track = (
        await c.post(
            T,
            json={
                "profile_id": p["id"],
                "name": "Backend",
                "nl_text": "backend engineer Python",
                "criteria": {
                    "titles": [{"title": "Backend Engineer", "synonyms": [], "exclude": False}],
                    "skills": {"must": ["Python"], "nice": ["PostgreSQL"], "exclude": []},
                },
            },
            headers=h,
        )
    ).json()

    engine = create_async_engine(TEST_OWNER_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await set_request_context(session, user_id=str(me.id), workspace_id=str(me.personal))
        job = Job(
            title="Backend Engineer",
            normalized_title="backend engineer",
            description_text=(
                "Requirements:\n- Python\n- PostgreSQL\n- FastAPI preferred\n"
                "We scale product APIs for customers remotely.\n"
            ),
            description_html="<p>Python PostgreSQL</p>",
            content_hash=f"tailor-{uuid.uuid4().hex}",
            simhash=42,
            canonical_url=f"https://example.com/jobs/{uuid.uuid4().hex}",
            apply_url=f"https://boards.greenhouse.io/acme/jobs/{uuid.uuid4().hex[:8]}",
            status="open",
            skills=["Python", "PostgreSQL", "FastAPI"],
            work_mode="remote",
        )
        session.add(job)
        await session.flush()
        tj = TrackJob(
            workspace_id=uuid.UUID(str(me.personal)),
            track_id=uuid.UUID(track["id"]),
            job_id=job.id,
            status="new",
            eligibility="eligible",
        )
        session.add(tj)
        await session.commit()
        job_id = str(job.id)
        tj_id = str(tj.id)
    await engine.dispose()
    return p, track, job_id, tj_id, h


@pytest.mark.asyncio
async def test_tailor_accept_creates_application(env_t):
    c = env_t
    me = await signup(c)
    _p, _track, _job_id, tj_id, h = await _seed(c, me)

    started = await c.post(
        f"/api/v1/track-jobs/{tj_id}/tailor",
        json={"include_cover_letter": True},
        headers=h,
    )
    assert started.status_code == 201, started.text
    run = started.json()
    assert run["status"] == "ready"
    assert run["lens_before"].get("grade")
    assert run["lens_after"].get("grade")
    assert run["draft_version_id"]
    assert run.get("cover_letter")
    assert 120 <= (run["cover_letter"]["word_count"] or 0) <= 280

    accepted = await c.post(
        f"/api/v1/tailor-runs/{run['id']}/accept",
        json={"include_cover_letter": True},
        headers=h,
    )
    assert accepted.status_code == 200, accepted.text
    app = accepted.json()
    assert app["status"] in {"ready", "job_closed"}
    assert app["resume_version_id"] == run["draft_version_id"]

    listed = await c.get("/api/v1/applications", headers=h)
    assert listed.status_code == 200
    assert any(a["id"] == app["id"] for a in listed.json()["items"])

    # Re-tailor creates new draft; application points at latest
    again = await c.post(
        f"/api/v1/track-jobs/{tj_id}/tailor",
        json={"include_cover_letter": False},
        headers=h,
    )
    assert again.status_code == 201, again.text
    run2 = again.json()
    acc2 = await c.post(f"/api/v1/tailor-runs/{run2['id']}/accept", json={}, headers=h)
    assert acc2.status_code == 200, acc2.text
    assert acc2.json()["id"] == app["id"]
    assert acc2.json()["resume_version_id"] == run2["draft_version_id"]


@pytest.mark.asyncio
async def test_tailor_cross_tenant_404(env_t):
    c = env_t
    a = await signup(c)
    b = await signup(c)
    _p, _t, _j, tj_id, ah = await _seed(c, a)
    started = await c.post(f"/api/v1/track-jobs/{tj_id}/tailor", json={}, headers=ah)
    assert started.status_code == 201
    run_id = started.json()["id"]
    bh = b.h(b.personal)
    assert (await c.get(f"/api/v1/tailor-runs/{run_id}", headers=bh)).status_code == 404
    assert (
        await c.post(f"/api/v1/tailor-runs/{run_id}/accept", json={}, headers=bh)
    ).status_code == 404
    assert (
        await c.post(f"/api/v1/track-jobs/{tj_id}/tailor", json={}, headers=bh)
    ).status_code == 404


@pytest.mark.asyncio
async def test_applications_rls_wrong_workspace(env_t):
    c = env_t
    me = await signup(c)
    _p, _t, _j, tj_id, h = await _seed(c, me)
    started = await c.post(f"/api/v1/track-jobs/{tj_id}/tailor", json={}, headers=h)
    assert started.status_code == 201
    await c.post(f"/api/v1/tailor-runs/{started.json()['id']}/accept", json={}, headers=h)

    engine = create_async_engine(TEST_OWNER_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(text("SET ROLE kame_apply_app"))
        await set_request_context(session, user_id=str(me.id), workspace_id=str(uuid.uuid4()))
        n = (await session.execute(text("SELECT count(*) FROM applications"))).scalar_one()
        assert int(n) == 0
        n2 = (await session.execute(text("SELECT count(*) FROM tailor_runs"))).scalar_one()
        assert int(n2) == 0
        n3 = (await session.execute(text("SELECT count(*) FROM cover_letters"))).scalar_one()
        assert int(n3) == 0
        await session.execute(text("RESET ROLE"))
    await engine.dispose()
