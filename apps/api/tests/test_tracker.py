"""Phase 11: applications tracker, mark applied, metrics, home, RLS."""

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
async def env_tr():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c


async def _seed_track_job(c, me):
    h = me.h(me.personal)
    p = (await c.post(P, json={"display_name": "Tracker User"}, headers=h)).json()
    track = (
        await c.post(
            T,
            json={
                "profile_id": p["id"],
                "name": "Backend",
                "nl_text": "backend",
                "criteria": {
                    "titles": [{"title": "Engineer", "synonyms": [], "exclude": False}],
                    "skills": {"must": ["Python"], "nice": [], "exclude": []},
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
            description_text="Python FastAPI",
            description_html="<p>Python</p>",
            content_hash=f"trk-{uuid.uuid4().hex[:12]}",
            simhash=7,
            canonical_url=f"https://example.com/j/{uuid.uuid4().hex[:8]}",
            apply_url=f"https://boards.example.com/{uuid.uuid4().hex[:8]}",
            status="open",
            skills=["Python"],
            meta={"company_name": "Acme"},
        )
        session.add(job)
        await session.flush()
        tj = TrackJob(
            workspace_id=me.personal,
            track_id=track["id"],
            job_id=job.id,
            status="new",
            score=0.8,
        )
        session.add(tj)
        await session.commit()
        job_id, tj_id = job.id, tj.id
    await engine.dispose()
    return h, track, job_id, tj_id


@pytest.mark.asyncio
async def test_mark_applied_status_and_kpis(env_tr):
    c = env_tr
    me = await signup(c)
    h, _track, _job_id, tj_id = await _seed_track_job(c, me)

    marked = await c.post(
        "/api/v1/applications/mark-applied",
        json={"track_job_id": str(tj_id), "method": "manual"},
        headers=h,
    )
    assert marked.status_code == 201, marked.text
    app = marked.json()
    assert app["status"] == "submitted"
    assert app["company_name"] == "Acme"
    assert app["follow_up_draft"]
    assert app["reminder_at"]

    # Status → responded
    patched = await c.patch(
        f"/api/v1/applications/{app['id']}/status",
        json={"status": "responded"},
        headers=h,
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["status"] == "responded"

    metrics = await c.get("/api/v1/metrics?period=total", headers=h)
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["kpis"]["submitted"] >= 1
    assert body["funnel"]["responded"] >= 1

    home = await c.get("/api/v1/home?period=total", headers=h)
    assert home.status_code == 200
    assert "headline" in home.json()
    assert "tracks" in home.json()

    listed = await c.get("/api/v1/applications", headers=h)
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1


@pytest.mark.asyncio
async def test_manual_create_and_export(env_tr):
    c = env_tr
    me = await signup(c)
    h, track, *_ = await _seed_track_job(c, me)

    created = await c.post(
        "/api/v1/applications/manual",
        json={
            "track_id": track["id"],
            "company": "Globex",
            "title": "Staff Engineer",
            "url": "https://globex.example/jobs/1",
        },
        headers=h,
    )
    assert created.status_code == 201, created.text
    assert created.json()["status"] == "submitted"

    export = await c.get("/api/v1/applications/export?fmt=csv", headers=h)
    assert export.status_code == 200
    assert b"Globex" in export.content


@pytest.mark.asyncio
async def test_applications_rls(env_tr):
    c = env_tr
    me = await signup(c)
    h, track, *_ = await _seed_track_job(c, me)
    created = (
        await c.post(
            "/api/v1/applications/manual",
            json={"track_id": track["id"], "company": "X", "title": "Y"},
            headers=h,
        )
    ).json()

    engine = create_async_engine(TEST_DB_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await set_request_context(
            session, user_id=str(me.id), workspace_id="00000000-0000-0000-0000-000000000099"
        )
        n = (
            await session.execute(
                text("SELECT count(*) FROM applications WHERE id = :id"),
                {"id": created["id"]},
            )
        ).scalar_one()
        assert n == 0
    await engine.dispose()


@pytest.mark.asyncio
async def test_duplicate_warning_and_regression_note(env_tr):
    c = env_tr
    me = await signup(c)
    h, _track, _job_id, tj_id = await _seed_track_job(c, me)

    first = await c.post(
        "/api/v1/applications/mark-applied",
        json={"track_job_id": str(tj_id), "method": "manual"},
        headers=h,
    )
    assert first.status_code == 201, first.text
    app_id = first.json()["id"]

    # second mark on same job → duplicate_warning
    again = await c.post(
        "/api/v1/applications/mark-applied",
        json={"track_job_id": str(tj_id), "method": "manual"},
        headers=h,
    )
    assert again.status_code == 201, again.text
    assert again.json()["duplicate_warning"] is True

    to_interview = await c.patch(
        f"/api/v1/applications/{app_id}/status",
        json={"status": "interview"},
        headers=h,
    )
    # submitted → interview allowed
    assert to_interview.status_code == 200, to_interview.text

    bad = await c.patch(
        f"/api/v1/applications/{app_id}/status",
        json={"status": "rejected"},
        headers=h,
    )
    assert bad.status_code == 422

    ok = await c.patch(
        f"/api/v1/applications/{app_id}/status",
        json={"status": "rejected", "note": "role filled"},
        headers=h,
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "rejected"
