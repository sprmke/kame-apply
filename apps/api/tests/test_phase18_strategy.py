"""Phase 18: Be Found optimizer, consistency, caps, salary, follow-ups, freshness."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.rls import set_request_context
from app.jobs.models import Job, TrackJob
from app.main import create_app
from app.strategy.consistency import check_consistency
from app.strategy.freshness import freshness_for
from app.strategy.linkedin import build_suggestions
from app.strategy.salary import advise_salary
from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_workspaces import signup

P = "/api/v1/profiles"
T = "/api/v1/tracks"


@pytest.fixture
async def env_s18():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c


def test_headline_within_limit_and_truthful():
    result = build_suggestions(
        track_id=uuid.uuid4(),
        track_name="Backend",
        structured={
            "titles": [{"title": "Staff Engineer", "synonyms": [], "exclude": False}],
            "skills": {"must": ["Python", "Go"], "nice": ["Kubernetes"], "exclude": []},
        },
        display_name="Alex",
        headline=None,
        summary="Backend engineer.",
        location="Remote",
        experiences=[
            {
                "company": "Acme",
                "title": "Senior Engineer",
                "description": "Built APIs",
                "start_date": "2020-01-01",
            }
        ],
        skills=["Python", "Kubernetes", "SQL"],
    )
    assert result.headline.char_count <= 220
    assert "Senior Engineer" in result.headline.text
    assert "Go" not in result.skills_order  # not in profile
    assert "Python" in result.skills_order
    assert result.open_to_work
    assert result.github_checklist


def test_consistency_flags_missing_company():
    report = check_consistency(
        linkedin_text="Alex · Engineer at OtherCo",
        experiences=[{"company": "Acme", "title": "Engineer", "start_date": "2020-01-01"}],
        skills=["Python"],
        display_name="Alex",
        headline=None,
    )
    assert any(i.field == "company" and i.severity == "error" for i in report.issues)
    assert report.score < 100


def test_salary_respects_floor():
    advice = advise_salary(
        posting_salary={"min": 80_000, "max": 100_000, "currency": "USD"},
        user_salary_prefs={"floor": 90_000, "currency": "USD"},
    )
    assert advice.suggested_min == 90_000
    assert advice.suggested_max == 100_000
    assert advice.truthful is True


def test_freshness_high_boost():
    f = freshness_for(
        job_id=uuid.uuid4(),
        posted_at=datetime.now(UTC) - timedelta(hours=6),
        first_seen_at=None,
    )
    assert f.boost == "high"
    assert "6h" in f.label or "ago" in f.label


@pytest.mark.asyncio
async def test_optimize_and_consistency_api(env_s18):
    c = env_s18
    me = await signup(c)
    h = me.h(me.personal)
    p = (
        await c.post(P, json={"display_name": "Strategy User", "summary": "Builder"}, headers=h)
    ).json()
    # add experience
    await c.post(
        f"{P}/{p['id']}/experiences",
        json={
            "company": "Acme",
            "title": "Engineer",
            "start_date": "2021-01-01",
            "description": "Python services",
        },
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
                    "titles": [{"title": "Backend Engineer", "synonyms": [], "exclude": False}],
                    "skills": {"must": ["Python"], "nice": [], "exclude": []},
                },
            },
            headers=h,
        )
    ).json()

    opt = await c.get(f"/api/v1/tracks/{track['id']}/linkedin-optimize", headers=h)
    assert opt.status_code == 200, opt.text
    body = opt.json()
    assert body["headline"]["char_count"] <= 220
    assert body["headline"]["why"]
    assert body["open_to_work"]

    cons = await c.post(
        "/api/v1/strategy/consistency",
        json={
            "track_id": track["id"],
            "linkedin_text": "Strategy User\nEngineer at Acme\nPython",
        },
        headers=h,
    )
    assert cons.status_code == 200, cons.text
    assert "score" in cons.json()


@pytest.mark.asyncio
async def test_cap_salary_followup_freshness(env_s18):
    c = env_s18
    me = await signup(c)
    h = me.h(me.personal)
    p = (
        await c.post(
            P,
            json={
                "display_name": "Cap User",
                "salary_prefs": {"floor": 100000, "currency": "USD"},
            },
            headers=h,
        )
    ).json()
    patched = await c.patch(
        f"{P}/{p['id']}",
        json={"salary_prefs": {"floor": 100000, "currency": "USD"}},
        headers=h,
    )
    assert patched.status_code in {200, 204}, patched.text
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

    prefs = await c.put(
        "/api/v1/strategy/prefs",
        json={"company_cap": 2, "company_cap_window_days": 90},
        headers=h,
    )
    assert prefs.status_code == 200, prefs.text
    assert prefs.json()["company_cap"] == 2

    engine = create_async_engine(TEST_OWNER_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    app_ids = []
    async with factory() as session:
        await set_request_context(session, user_id=str(me.id), workspace_id=str(me.personal))
        for i in range(2):
            job = Job(
                title=f"Eng {i}",
                normalized_title=f"eng {i}",
                description_text="Python",
                description_html="<p>Python</p>",
                content_hash=f"s18-{uuid.uuid4().hex[:12]}",
                simhash=i + 1,
                canonical_url=f"https://example.com/j/{uuid.uuid4().hex[:8]}",
                apply_url=f"https://boards.greenhouse.io/acme/jobs/{i}",
                status="open",
                skills=["Python"],
                salary={"min": 90_000, "max": 120_000, "currency": "USD"},
                posted_at=datetime.now(UTC) - timedelta(hours=6),
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
            await session.flush()
            job_ids = (job.id, tj.id)
            app_ids.append(job_ids)
        await session.commit()
    await engine.dispose()

    marked = []
    for _job_id, tj_id in app_ids:
        r = await c.post(
            "/api/v1/applications/mark-applied",
            json={"track_job_id": str(tj_id), "method": "manual"},
            headers=h,
        )
        assert r.status_code == 201, r.text
        marked.append(r.json())

    cap = await c.get(f"/api/v1/applications/{marked[0]['id']}/company-cap", headers=h)
    assert cap.status_code == 200, cap.text
    assert cap.json()["exceeds"] is True or cap.json()["active_count"] >= 1

    sal = await c.get(f"/api/v1/applications/{marked[0]['id']}/salary-advice", headers=h)
    assert sal.status_code == 200, sal.text
    data = sal.json()
    assert data["posting_min"] == 90000
    assert data["suggested_min"] is not None
    # Floor from prefs raises posting min when set
    if data.get("user_floor"):
        assert data["suggested_min"] >= data["user_floor"]

    fu = await c.get(f"/api/v1/applications/{marked[0]['id']}/follow-up-drafts", headers=h)
    assert fu.status_code == 200, fu.text
    assert "week" in fu.json()["day_7"].lower() or "follow" in fu.json()["day_7"].lower()
    assert "two weeks" in fu.json()["day_14"].lower() or "check in" in fu.json()["day_14"].lower()

    fr = await c.get(f"/api/v1/jobs/{app_ids[0][0]}/freshness", headers=h)
    assert fr.status_code == 200, fr.text
    assert fr.json()["boost"] in {"high", "medium", "low", "none"}


@pytest.mark.asyncio
async def test_strategy_cross_tenant(env_s18):
    c = env_s18
    a = await signup(c)
    b = await signup(c)
    ah = a.h(a.personal)
    p = (await c.post(P, json={"display_name": "A"}, headers=ah)).json()
    track = (
        await c.post(
            T,
            json={
                "profile_id": p["id"],
                "name": "T",
                "nl_text": "x",
                "criteria": {
                    "titles": [{"title": "Eng", "synonyms": [], "exclude": False}],
                    "skills": {"must": [], "nice": [], "exclude": []},
                },
            },
            headers=ah,
        )
    ).json()
    bh = b.h(b.personal)
    r = await c.get(f"/api/v1/tracks/{track['id']}/linkedin-optimize", headers=bh)
    assert r.status_code == 404
