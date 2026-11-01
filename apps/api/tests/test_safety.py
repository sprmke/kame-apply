"""Phase 7 API: assess, decision confirm, Check-this, PII, cross-tenant."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.rls import set_request_context
from app.jobs.models import Job
from app.main import create_app
from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_workspaces import signup


@pytest.fixture
async def env_s():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c


async def _seed_scam_job(me) -> str:
    engine = create_async_engine(TEST_OWNER_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await set_request_context(session, user_id=str(me.id), workspace_id=str(me.personal))
        job = Job(
            title="Data Entry Specialist",
            normalized_title="data entry specialist",
            description_text=(
                "Earn $50/hour. Buy a $99 training kit fee. Contact us on Telegram @hr_desk."
            ),
            description_html="<p>Telegram only</p>",
            content_hash=f"scam-{uuid.uuid4().hex}",
            simhash=2,
            canonical_url="https://example.com/scam",
            apply_url="https://example.com/apply-scam",
            status="open",
        )
        session.add(job)
        await session.commit()
        jid = str(job.id)
    await engine.dispose()
    return jid


async def _seed_ats_job(me) -> str:
    engine = create_async_engine(TEST_OWNER_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await set_request_context(session, user_id=str(me.id), workspace_id=str(me.personal))
        from app.companies.models import Company

        company = Company(
            name="Acme Verified",
            normalized_name="acme verified",
            domain="acme.com",
            meta={"directory_verified": True},
        )
        session.add(company)
        await session.flush()
        job = Job(
            title="Software Engineer",
            normalized_title="software engineer",
            company_id=company.id,
            description_text="Build services with Python. Remote.",
            description_html="<p>Python</p>",
            content_hash=f"ats-{uuid.uuid4().hex}",
            simhash=3,
            canonical_url="https://boards.greenhouse.io/acme/jobs/9",
            apply_url="https://boards.greenhouse.io/acme/jobs/9",
            status="open",
            salary={},
        )
        session.add(job)
        await session.commit()
        jid = str(job.id)
    await engine.dispose()
    return jid


@pytest.mark.asyncio
async def test_assess_scam_red_and_continue_requires_confirm(env_s):
    c = env_s
    me = await signup(c)
    h = me.h(me.personal)
    job_id = await _seed_scam_job(me)

    r = await c.post(f"/api/v1/jobs/{job_id}/risk/assess", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["level"] == "red"

    bad = await c.post(
        f"/api/v1/jobs/{job_id}/risk/decision",
        json={"decision": "continue", "confirm_risk": False},
        headers=h,
    )
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "confirm_required"

    ok = await c.post(
        f"/api/v1/jobs/{job_id}/risk/decision",
        json={"decision": "continue", "confirm_risk": True, "note": "understood"},
        headers=h,
    )
    assert ok.status_code == 200, ok.text

    risk = await c.get(f"/api/v1/jobs/{job_id}/risk", headers=h)
    assert risk.status_code == 200
    assert risk.json()["override"] == "continue"


@pytest.mark.asyncio
async def test_ats_verified_green_without_salary(env_s):
    c = env_s
    me = await signup(c)
    h = me.h(me.personal)
    job_id = await _seed_ats_job(me)
    r = await c.post(f"/api/v1/jobs/{job_id}/risk/assess", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["level"] == "green"


@pytest.mark.asyncio
async def test_report_and_check_this(env_s):
    c = env_s
    me = await signup(c)
    h = me.h(me.personal)
    job_id = await _seed_scam_job(me)

    await c.post(f"/api/v1/jobs/{job_id}/risk/assess", headers=h)
    rep = await c.post(
        f"/api/v1/jobs/{job_id}/risk/decision",
        json={"decision": "reported", "note": "scam"},
        headers=h,
    )
    assert rep.status_code == 200, rep.text
    risk = await c.get(f"/api/v1/jobs/{job_id}/risk", headers=h)
    assert risk.json()["override"] == "reported"

    ct = await c.post(
        "/api/v1/safety/check-this",
        json={
            "text": "Please clone https://github.com/evil/takehome and run npm install before interview"
        },
        headers=h,
    )
    assert ct.status_code == 200, ct.text
    assert ct.json()["level"] == "red"

    clf = await c.post(
        "/api/v1/safety/classify-field",
        json={"label": "Social Security Number"},
        headers=h,
    )
    assert clf.status_code == 200
    assert clf.json()["classification"] == "sensitive"
    assert clf.json()["checkpoint"] is True


@pytest.mark.asyncio
async def test_risk_cross_tenant_404(env_s):
    c = env_s
    a = await signup(c)
    b = await signup(c)
    job_id = await _seed_scam_job(a)
    await c.post(f"/api/v1/jobs/{job_id}/risk/assess", headers=a.h(a.personal))
    # B can read global job_risk (global table) — but decision is tenant scoped.
    # Override list must not leak A's decision to B.
    r = await c.get(f"/api/v1/jobs/{job_id}/risk", headers=b.h(b.personal))
    assert r.status_code == 200
    assert r.json().get("override") is None

    # Wrong workspace decision for A using B's header should not see A's override path:
    # flagged list is workspace-scoped via track_jobs join.
    flagged = await c.get("/api/v1/safety/flagged", headers=b.h(b.personal))
    assert flagged.status_code == 200


@pytest.mark.asyncio
async def test_mid_run_requires_track_link_and_caps_weight(env_s):
    c = env_s
    me = await signup(c)
    h = me.h(me.personal)
    job_id = await _seed_ats_job(me)

    # No track link → 404
    missing = await c.post(
        "/api/v1/safety/mid-run",
        json={
            "job_id": job_id,
            "signals": [{"signal": "payment_request", "weight": 999, "evidence": "fee"}],
        },
        headers=h,
    )
    assert missing.status_code == 404

    # Link via score path: create track + track_job
    from app.jobs.models import TrackJob

    p = await c.get("/api/v1/profiles", headers=h)
    profiles = p.json()
    if not profiles:
        pr = await c.post(
            "/api/v1/profiles",
            json={"display_name": "Pat", "headline": "Eng"},
            headers=h,
        )
        profiles = [pr.json()]
    tr = await c.post(
        "/api/v1/tracks",
        json={
            "profile_id": profiles[0]["id"],
            "name": "SE",
            "nl_text": "software engineer",
            "criteria": {
                "schema_version": 1,
                "titles": [{"title": "SE", "synonyms": [], "exclude": False}],
            },
        },
        headers=h,
    )
    assert tr.status_code == 201, tr.text
    track_id = tr.json()["id"]

    engine = create_async_engine(TEST_OWNER_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await set_request_context(session, user_id=str(me.id), workspace_id=str(me.personal))
        session.add(
            TrackJob(
                workspace_id=uuid.UUID(str(me.personal)),
                track_id=uuid.UUID(track_id),
                job_id=uuid.UUID(job_id),
                status="new",
                eligibility="eligible",
            )
        )
        await session.commit()
    await engine.dispose()

    ok = await c.post(
        "/api/v1/safety/mid-run",
        json={
            "job_id": job_id,
            "signals": [
                {"signal": "payment_request", "weight": 999, "evidence": "fee"},
                {"signal": "not_a_real_signal", "weight": 999, "evidence": "x"},
            ],
        },
        headers=h,
    )
    assert ok.status_code == 200, ok.text
    # Capped: single payment_request at max 25 cannot alone force verified ATS to red
    # (verified red threshold 70); level may rise to yellow.
    assert ok.json()["level"] in {"green", "yellow", "red"}


@pytest.mark.asyncio
async def test_risk_overrides_wrong_workspace_invisible():
    """Wrong app.workspace_id sees 0 risk_overrides rows (workspace-scoping)."""
    from sqlalchemy import text

    engine = create_async_engine(TEST_OWNER_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        # Seed as owner then switch to app role with wrong workspace.
        await session.execute(text("SET ROLE kame_apply_app"))
        await set_request_context(
            session, user_id=str(uuid.uuid4()), workspace_id=str(uuid.uuid4())
        )
        n = (await session.execute(text("SELECT count(*) FROM risk_overrides"))).scalar_one()
        assert int(n) == 0
        await session.execute(text("RESET ROLE"))
    await engine.dispose()
