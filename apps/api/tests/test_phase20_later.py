"""Phase 20: responses, interview prep, gaps, referrals, coach."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.rls import set_request_context
from app.jobs.models import Job, TrackJob
from app.main import create_app
from app.responses.classify import classify_reply
from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_workspaces import signup

P = "/api/v1/profiles"
T = "/api/v1/tracks"


@pytest.fixture
async def env_s20():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c


def test_classify_rejection_and_scam():
    r = classify_reply(
        subject="Update",
        body="Unfortunately we will not be moving forward with your application.",
    )
    assert r.classification == "rejection"
    assert r.confidence >= 0.8

    scam = classify_reply(
        subject="Offer",
        body="Please wire payment via Western Union to start onboarding.",
    )
    assert scam.scam_level == "red"
    assert "payment_request" in scam.scam_reasons


async def _seed_app(c, me):
    h = me.h(me.personal)
    p = (await c.post(P, json={"display_name": "Phase20"}, headers=h)).json()
    await c.post(
        f"{P}/{p['id']}/experiences",
        json={
            "company": "Acme",
            "title": "Engineer",
            "start_date": "2021-01-01",
            "description": "Built Python APIs",
        },
        headers=h,
    )
    await c.post(
        f"{P}/{p['id']}/skills",
        json={"name": "Python"},
        headers=h,
    )
    track = (
        await c.post(
            T,
            json={
                "profile_id": p["id"],
                "name": "Backend",
                "nl_text": "backend",
                "criteria": {
                    "titles": [{"title": "Engineer", "synonyms": [], "exclude": False}],
                    "skills": {"must": ["Python", "Kubernetes"], "nice": [], "exclude": []},
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
            description_text="Python and Kubernetes",
            description_html="<p>Python</p>",
            content_hash=f"s20-{uuid.uuid4().hex[:12]}",
            simhash=42,
            canonical_url=f"https://example.com/j/{uuid.uuid4().hex[:8]}",
            apply_url="https://boards.greenhouse.io/acme/jobs/1",
            status="open",
            skills=["Python"],
            meta={"company_name": "Acme Corp"},
        )
        session.add(job)
        await session.flush()
        tj = TrackJob(
            workspace_id=me.personal,
            track_id=track["id"],
            job_id=job.id,
            status="new",
            score=0.9,
        )
        session.add(tj)
        await session.flush()
        tj_id = tj.id
        await session.commit()
    await engine.dispose()

    marked = await c.post(
        "/api/v1/applications/mark-applied",
        json={"track_job_id": str(tj_id), "method": "manual"},
        headers=h,
    )
    assert marked.status_code == 201, marked.text
    return h, p, track, marked.json()


@pytest.mark.asyncio
async def test_response_propose_and_accept(env_s20):
    c = env_s20
    me = await signup(c)
    h, _p, _track, app = await _seed_app(c, me)

    ingest = await c.post(
        "/api/v1/responses/ingest",
        json={
            "application_id": app["id"],
            "sender": "recruiter@acme.test",
            "subject": "Interview",
            "body_text": "We would like to schedule an interview next Tuesday.",
        },
        headers=h,
    )
    assert ingest.status_code == 200, ingest.text
    body = ingest.json()
    assert body["message"]["classification"] == "interview"
    assert body["proposal"] is not None
    assert body["proposal"]["to_status"] == "interview"

    props = await c.get("/api/v1/responses/proposals", headers=h)
    assert props.status_code == 200
    assert len(props.json()) >= 1
    pid = body["proposal"]["id"]

    decided = await c.post(
        f"/api/v1/responses/proposals/{pid}/decide",
        json={"accept": True},
        headers=h,
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "accepted"

    detail = await c.get(f"/api/v1/applications/{app['id']}", headers=h)
    assert detail.json()["status"] == "interview"


@pytest.mark.asyncio
async def test_interview_gaps_referrals_coach(env_s20):
    c = env_s20
    me = await signup(c)
    h, _p, track, app = await _seed_app(c, me)

    prep = await c.post(f"/api/v1/applications/{app['id']}/interview-prep", headers=h)
    assert prep.status_code == 200, prep.text
    assert prep.json()["company_brief"]
    assert prep.json()["likely_questions"]

    gaps = await c.post(f"/api/v1/tracks/{track['id']}/gap-plan/refresh", headers=h)
    assert gaps.status_code == 200, gaps.text
    skills = {g["skill"] for g in gaps.json()}
    assert "Kubernetes" in skills
    assert "Python" not in skills  # already on profile

    item = next(g for g in gaps.json() if g["skill"] == "Kubernetes")
    patched = await c.patch(f"/api/v1/gap-plan/{item['id']}", json={"status": "done"}, headers=h)
    assert patched.status_code == 200
    assert patched.json()["status"] == "done"

    imported = await c.post(
        "/api/v1/contacts/import",
        json={
            "contacts": [
                {
                    "name": "Sam Recruiter",
                    "email": "sam@acme.test",
                    "company": "Acme Corp",
                    "title": "Eng Manager",
                }
            ]
        },
        headers=h,
    )
    assert imported.status_code == 200
    assert imported.json()["imported"] == 1

    matches = await c.get(f"/api/v1/applications/{app['id']}/referral-matches", headers=h)
    assert matches.status_code == 200
    assert len(matches.json()) >= 1
    contact_id = matches.json()[0]["contact"]["id"]

    draft = await c.post(
        f"/api/v1/applications/{app['id']}/referral-drafts",
        json={"contact_id": contact_id},
        headers=h,
    )
    assert draft.status_code == 200, draft.text
    assert "Hi" in draft.json()["draft"]

    coach = await c.get("/api/v1/coach/profiles", headers=h)
    assert coach.status_code == 200
    assert any(row["application_count"] >= 1 for row in coach.json())


@pytest.mark.asyncio
async def test_phase20_cross_tenant(env_s20):
    c = env_s20
    a = await signup(c)
    b = await signup(c)
    ah = a.h(a.personal)
    _h, _p, track, app = await _seed_app(c, a)
    bh = b.h(b.personal)

    r1 = await c.get(f"/api/v1/applications/{app['id']}/interview-prep", headers=bh)
    assert r1.status_code == 404

    r2 = await c.get(f"/api/v1/tracks/{track['id']}/gap-plan", headers=bh)
    assert r2.status_code == 404

    # Seed a proposal as A, B must not see it
    await c.post(
        "/api/v1/responses/ingest",
        json={
            "application_id": app["id"],
            "subject": "Interview",
            "body_text": "Please schedule an interview call.",
        },
        headers=ah,
    )
    props = await c.get("/api/v1/responses/proposals", headers=bh)
    assert props.status_code == 200
    assert props.json() == []
