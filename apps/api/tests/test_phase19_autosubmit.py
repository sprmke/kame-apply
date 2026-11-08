"""Phase 19: auto-submit policy engine, dry-run, kill switches, batch approve."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.autosubmit.policy import evaluate
from app.core.config import Settings
from app.core.rls import set_request_context
from app.jobs.models import Job, TrackJob
from app.main import create_app
from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_phase15_runs import _seed_ready_application
from tests.test_workspaces import signup

P = "/api/v1/profiles"
T = "/api/v1/tracks"


def test_policy_blocks_linkedin():
    v = evaluate(
        autonomy="auto_submit",
        ats="linkedin",
        risk_level="green",
        match_score=90,
        score_threshold=75,
        answers_all_approved=True,
        checkpoint_fired=False,
        company_cap_exceeded=False,
        daily_cap_exceeded=False,
        job_open=True,
        job_fresh_enough=True,
        kill_switch_track=False,
        kill_switch_workspace=False,
        global_enabled=True,
        live_enabled=True,
        dry_run_remaining=0,
    )
    assert v.allow_submit is False
    assert any(r.code == "platform" and not r.ok for r in v.reasons)


def test_policy_dry_run_when_budget_remaining():
    v = evaluate(
        autonomy="auto_submit",
        ats="greenhouse",
        risk_level="green",
        match_score=90,
        score_threshold=75,
        answers_all_approved=True,
        checkpoint_fired=False,
        company_cap_exceeded=False,
        daily_cap_exceeded=False,
        job_open=True,
        job_fresh_enough=True,
        kill_switch_track=False,
        kill_switch_workspace=False,
        global_enabled=True,
        live_enabled=False,
        dry_run_remaining=5,
    )
    assert v.dry_run is True
    assert v.allow_submit is False


def test_policy_live_when_ready():
    v = evaluate(
        autonomy="auto_submit",
        ats="greenhouse",
        risk_level="green",
        match_score=90,
        score_threshold=75,
        answers_all_approved=True,
        checkpoint_fired=False,
        company_cap_exceeded=False,
        daily_cap_exceeded=False,
        job_open=True,
        job_fresh_enough=True,
        kill_switch_track=False,
        kill_switch_workspace=False,
        global_enabled=True,
        live_enabled=True,
        dry_run_remaining=0,
    )
    assert v.allow_submit is True
    assert v.dry_run is False


@pytest.fixture
async def env_a19():
    settings = Settings(
        database_url=TEST_DB_URL,
        environment="test",
        log_json=False,
        auth_rate_limit_enabled=False,
        auto_submit_enabled=True,
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c


@pytest.mark.asyncio
async def test_settings_explain_and_kill(env_a19):
    c = env_a19
    me = await signup(c)
    h = me.h(me.personal)
    p = (await c.post(P, json={"display_name": "AS User"}, headers=h)).json()
    track = (
        await c.post(
            T,
            json={
                "profile_id": p["id"],
                "name": "AS Track",
                "autonomy": "auto_submit",
                "nl_text": "eng",
                "criteria": {
                    "titles": [{"title": "Engineer", "synonyms": [], "exclude": False}],
                    "skills": {"must": ["Python"], "nice": [], "exclude": []},
                },
            },
            headers=h,
        )
    ).json()

    cfg = await c.get(f"/api/v1/tracks/{track['id']}/auto-submit", headers=h)
    assert cfg.status_code == 200, cfg.text
    assert cfg.json()["dry_run_remaining"] == 10
    assert cfg.json()["global_enabled"] is True

    # Cannot enable live while dry-runs remain
    live = await c.put(
        f"/api/v1/tracks/{track['id']}/auto-submit",
        json={"live_enabled": True},
        headers=h,
    )
    assert live.status_code == 409

    # Exhaust dry-runs via settings then enable live
    ok = await c.put(
        f"/api/v1/tracks/{track['id']}/auto-submit",
        json={"dry_run_remaining": 0, "live_enabled": True, "score_threshold": 70},
        headers=h,
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["live_enabled"] is True

    engine = create_async_engine(TEST_OWNER_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await set_request_context(session, user_id=str(me.id), workspace_id=str(me.personal))
        job = Job(
            title="Eng",
            normalized_title="eng",
            description_text="Python",
            description_html="<p>Python</p>",
            content_hash=f"a19-{uuid.uuid4().hex[:12]}",
            simhash=11,
            canonical_url=f"https://example.com/j/{uuid.uuid4().hex[:8]}",
            apply_url="https://boards.greenhouse.io/acme/jobs/1",
            status="open",
            skills=["Python"],
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
            score=0.9,
        )
        session.add(tj)
        await session.commit()
        tj_id = tj.id
    await engine.dispose()

    marked = await c.post(
        "/api/v1/applications/mark-applied",
        json={"track_job_id": str(tj_id), "method": "manual"},
        headers=h,
    )
    assert marked.status_code == 201, marked.text
    app_id = marked.json()["id"]

    expl = await c.get(f"/api/v1/applications/{app_id}/auto-submit/explain", headers=h)
    assert expl.status_code == 200, expl.text
    assert "verdict" in expl.json()
    assert expl.json()["verdict"]["reasons"]

    kill = await c.post(
        "/api/v1/workspaces/auto-submit/kill",
        json={"enabled": True},
        headers=h,
    )
    assert kill.status_code == 200, kill.text
    expl2 = await c.get(f"/api/v1/applications/{app_id}/auto-submit/explain", headers=h)
    assert expl2.json()["verdict"]["allow_submit"] is False


@pytest.mark.asyncio
async def test_batch_approve_and_cross_tenant(env_a19):
    c = env_a19
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
                "autonomy": "assist",
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
    r = await c.get(f"/api/v1/tracks/{track['id']}/auto-submit", headers=bh)
    assert r.status_code == 404

    # Batch approve empty / unknown ids → 0 updated
    ba = await c.post(
        "/api/v1/auto-submit/batch-approve",
        json={"answer_bank_ids": [str(uuid.uuid4())], "approved": True},
        headers=ah,
    )
    assert ba.status_code == 200
    assert ba.json()["updated"] == 0


@pytest.fixture
async def env_auto():
    settings = Settings(
        database_url=TEST_DB_URL,
        environment="test",
        log_json=False,
        auth_rate_limit_enabled=False,
        auto_submit_enabled=True,
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c


@pytest.mark.asyncio
async def test_live_auto_submit_authorizes_the_run(env_auto):
    c = env_auto
    me = await signup(c)
    h, app_id, _pid = await _seed_ready_application(
        c, me, apply_url="https://boards.greenhouse.io/acme/jobs/auto"
    )
    application = (await c.get(f"/api/v1/applications/{app_id}", headers=h)).json()
    track_id = application["track_id"]

    patched = await c.patch(
        f"/api/v1/tracks/{track_id}", json={"autonomy": "auto_submit"}, headers=h
    )
    assert patched.status_code == 200, patched.text
    auto = await c.put(
        f"/api/v1/tracks/{track_id}/auto-submit",
        json={"live_enabled": True, "dry_run_remaining": 0, "score_threshold": 70},
        headers=h,
    )
    assert auto.status_code == 200, auto.text

    started = await c.post(
        "/api/v1/runs/runner/start",
        json={"application_id": app_id, "allow_submit": True},
        headers=h,
    )
    assert started.status_code == 201, started.text
    body = started.json()
    assert body["policy"]["auto_submit"]["allow_submit"] is True
    assert body["submit_approved"] is True
