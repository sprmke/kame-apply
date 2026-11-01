"""Phase 15: apply runs, runner tokens, checkpoints, no-submit-without-approval, RLS."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.applications.models import Application
from app.core.config import Settings
from app.core.rls import set_request_context
from app.jobs.models import Job, TrackJob
from app.main import create_app
from app.resumes.models import ResumeVersion
from app.runs.ats import NO_AUTO_SUBMIT, detect_ats
from app.runs.tokens import hash_token, looks_like_runner_token
from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_profiles import make_profile
from tests.test_workspaces import signup

FIXTURES = Path(__file__).resolve().parents[2] / "runner" / "fixtures"


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


def test_detect_ats_and_no_auto_submit():
    assert detect_ats("https://boards.greenhouse.io/acme/jobs/1") == "greenhouse"
    assert detect_ats("https://jobs.lever.co/acme") == "lever"
    assert detect_ats("https://www.linkedin.com/jobs/view/1") == "linkedin"
    assert "linkedin" in NO_AUTO_SUBMIT
    assert "greenhouse" not in NO_AUTO_SUBMIT


def test_fixture_forms_exist():
    assert (FIXTURES / "greenhouse.html").is_file()
    assert (FIXTURES / "lever.html").is_file()
    assert (FIXTURES / "ashby.html").is_file()
    assert (FIXTURES / "sensitive.html").is_file()


async def _seed_ready_application(c, me, *, apply_url: str):
    h = me.h(me.personal)
    p = await make_profile(c, me)
    track = (
        await c.post(
            "/api/v1/tracks",
            json={
                "profile_id": p["id"],
                "name": "Runner Track",
                "nl_text": "engineer",
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
            description_text="Python",
            description_html="<p>Python</p>",
            content_hash=f"run-{uuid.uuid4().hex[:12]}",
            simhash=11,
            canonical_url=f"https://example.com/j/{uuid.uuid4().hex[:8]}",
            apply_url=apply_url,
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
            score=0.9,
        )
        session.add(tj)
        rv = ResumeVersion(
            workspace_id=me.personal,
            profile_id=uuid.UUID(p["id"]),
            track_id=track["id"],
            kind="base",
            label="Base",
            content={"summary": "Engineer"},
            r2_pdf=f"ws/{me.personal}/resumes/base.pdf",
        )
        session.add(rv)
        await session.flush()
        app = Application(
            workspace_id=me.personal,
            track_id=track["id"],
            job_id=job.id,
            profile_id=uuid.UUID(p["id"]),
            status="ready",
            method="manual",
            resume_version_id=rv.id,
            apply_url=apply_url,
            company_name="Acme",
            job_title="Backend Engineer",
        )
        session.add(app)
        await session.commit()
        app_id = app.id
    await engine.dispose()
    return h, str(app_id), p["id"]


@pytest.mark.asyncio
async def test_runner_token_start_claim_checkpoint_no_submit(env_r):
    c = env_r
    me = await signup(c)
    h, app_id, _pid = await _seed_ready_application(
        c, me, apply_url="https://boards.greenhouse.io/acme/jobs/123"
    )

    tok = await c.post("/api/v1/runs/tokens", json={"label": "local", "mode": "local"}, headers=h)
    assert tok.status_code == 201, tok.text
    raw = tok.json()["token"]
    assert looks_like_runner_token(raw)
    rh = {
        "Authorization": f"Bearer {raw}",
        "X-Workspace-Id": str(me.personal),
    }

    listed = await c.get("/api/v1/runs/tokens", headers=h)
    assert listed.status_code == 200
    assert any(t["id"] == tok.json()["id"] for t in listed.json())

    started = await c.post(
        "/api/v1/runs/runner/start",
        json={"application_id": app_id, "allow_submit": True},
        headers=h,
    )
    assert started.status_code == 201, started.text
    run = started.json()
    assert run["status"] == "queued"
    assert run["ats"] == "greenhouse"
    assert run["profile_id"]
    assert run["policy"]["allow_submit"] is True

    empty = await c.post("/api/v1/runs/runner/claim", json={"runner_id": "r1"}, headers=rh)
    # First claim gets the run
    assert empty.status_code in {200, 201}
    claimed = empty.json()
    assert claimed["id"] == run["id"]
    assert claimed["status"] == "running"

    none = await c.post("/api/v1/runs/runner/claim", json={"runner_id": "r2"}, headers=rh)
    assert none.status_code == 204

    step = await c.post(
        f"/api/v1/runs/{run['id']}/steps",
        json={
            "seq": 1,
            "page_url": run["page_url"],
            "action": "fill",
            "field_label": "Email",
            "value_redacted": "[redacted]",
            "canonical_key": "email",
            "pii_class": "personal",
            "outcome": "ok",
        },
        headers=rh,
    )
    assert step.status_code == 201, step.text
    # Idempotent same seq
    again = await c.post(
        f"/api/v1/runs/{run['id']}/steps",
        json={"seq": 1, "action": "fill", "field_label": "Email"},
        headers=rh,
    )
    assert again.status_code == 201
    assert again.json()["id"] == step.json()["id"]

    cp = await c.post(
        f"/api/v1/runs/{run['id']}/checkpoints",
        json={"kind": "sensitive_field", "detail": {"label": "SSN"}},
        headers=rh,
    )
    assert cp.status_code == 201, cp.text
    assert cp.json()["status"] == "open"

    needs = await c.get("/api/v1/needs-you", headers=h)
    assert needs.status_code == 200
    assert any(i["kind"] == "apply_checkpoint" for i in needs.json()["items"])

    # Sensitive typed value never stored on checkpoint.decision
    resolved = await c.post(
        f"/api/v1/runs/checkpoints/{cp.json()['id']}/resolve",
        json={"decision": "typed_value", "value": "123-45-6789"},
        headers=rh,
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["decision"].get("value") is None
    assert resolved.json()["decision"].get("value_present") is True

    ephemeral = await c.get(f"/api/v1/runs/{run['id']}/ephemeral-sensitive", headers=rh)
    assert ephemeral.status_code == 200
    assert ephemeral.json()["value"] == "123-45-6789"
    gone = await c.get(f"/api/v1/runs/{run['id']}/ephemeral-sensitive", headers=rh)
    assert gone.json()["value"] is None

    final = await c.post(
        f"/api/v1/runs/{run['id']}/checkpoints",
        json={"kind": "final_review", "detail": {"message": "Review"}},
        headers=rh,
    )
    assert final.status_code == 201
    # Complete with confirmation without approve_submit → 409
    bad = await c.post(
        f"/api/v1/runs/{run['id']}/complete",
        params={"status": "completed", "confirmation": "true"},
        headers=rh,
    )
    assert bad.status_code == 409

    approve = await c.post(
        f"/api/v1/runs/checkpoints/{final.json()['id']}/resolve",
        json={"decision": "approve_submit"},
        headers=h,
    )
    assert approve.status_code == 200, approve.text

    ok = await c.post(
        f"/api/v1/runs/{run['id']}/complete",
        params={"status": "completed", "confirmation": "true"},
        headers=rh,
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["status"] == "completed"
    assert ok.json()["submit_approved"] is True

    app = await c.get(f"/api/v1/applications/{app_id}", headers=h)
    assert app.json()["status"] == "submitted"
    assert app.json()["method"] == "runner"


@pytest.mark.asyncio
async def test_linkedin_never_allow_submit(env_r):
    c = env_r
    me = await signup(c)
    h, app_id, _ = await _seed_ready_application(
        c, me, apply_url="https://www.linkedin.com/jobs/view/999"
    )
    started = await c.post(
        "/api/v1/runs/runner/start",
        json={"application_id": app_id, "allow_submit": True},
        headers=h,
    )
    assert started.status_code == 201, started.text
    assert started.json()["policy"]["allow_submit"] is False
    assert started.json()["policy"]["platform_no_auto_submit"] is True


@pytest.mark.asyncio
async def test_runs_cross_tenant_404(env_r):
    c = env_r
    a = await signup(c)
    b = await signup(c)
    ah, app_id, _ = await _seed_ready_application(c, a, apply_url="https://jobs.lever.co/acme/1")
    started = await c.post(
        "/api/v1/runs/runner/start",
        json={"application_id": app_id, "allow_submit": False},
        headers=ah,
    )
    assert started.status_code == 201
    run_id = started.json()["id"]
    bh = b.h(b.personal)
    assert (await c.get(f"/api/v1/runs/{run_id}", headers=bh)).status_code == 404
    assert (
        await c.post(
            f"/api/v1/runs/{run_id}/checkpoints",
            json={"kind": "login", "detail": {}},
            headers=bh,
        )
    ).status_code == 404


@pytest.mark.asyncio
async def test_runner_tokens_rls_wrong_workspace(env_r, tenancy):
    """Wrong app.workspace_id sees 0 runner_tokens rows."""
    engine = create_async_engine(TEST_OWNER_URL)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO runner_tokens (id, workspace_id, user_id, token_hash, label, mode) "
                "VALUES (:id, :w, :u, :h, 't', 'cloud')"
            ),
            {
                "id": uuid.uuid4(),
                "w": tenancy.ws_a,
                "u": tenancy.users["a_owner"],
                "h": hash_token("ka_run_test_hash_probe"),
            },
        )
    await engine.dispose()

    app_engine = create_async_engine(TEST_DB_URL)
    async with app_engine.connect() as conn:
        await conn.execute(
            text("SELECT set_config('app.workspace_id', :w, true)"), {"w": str(tenancy.ws_b)}
        )
        n = (await conn.execute(text("SELECT count(*) FROM runner_tokens"))).scalar_one()
        assert n == 0
    await app_engine.dispose()


@pytest.mark.asyncio
async def test_chaos_resume_from_last_step(env_r):
    """Kill mid-run: claim again after re-queue is not allowed; steps remain; resume via status."""
    c = env_r
    me = await signup(c)
    h, app_id, _ = await _seed_ready_application(c, me, apply_url="https://jobs.ashbyhq.com/acme/1")
    tok = await c.post("/api/v1/runs/tokens", json={"label": "cloud", "mode": "cloud"}, headers=h)
    raw = tok.json()["token"]
    rh = {"Authorization": f"Bearer {raw}", "X-Workspace-Id": str(me.personal)}

    started = await c.post(
        "/api/v1/runs/runner/start",
        json={"application_id": app_id, "allow_submit": False},
        headers=h,
    )
    run_id = started.json()["id"]
    claimed = await c.post("/api/v1/runs/runner/claim", json={"runner_id": "chaos-1"}, headers=rh)
    assert claimed.status_code == 200
    await c.post(
        f"/api/v1/runs/{run_id}/steps",
        json={"seq": 1, "action": "fill", "field_label": "Name", "outcome": "ok"},
        headers=rh,
    )
    await c.post(
        f"/api/v1/runs/{run_id}/steps",
        json={"seq": 2, "action": "fill", "field_label": "Email", "outcome": "ok"},
        headers=rh,
    )
    # Simulate crash: heartbeat stops; steps persist; last_step_seq is 2
    got = await c.get(f"/api/v1/runs/{run_id}", headers=rh)
    assert got.json()["last_step_seq"] == 2
    steps = await c.get(f"/api/v1/runs/{run_id}/steps", headers=rh)
    assert len(steps.json()) == 2
    # Re-claim does not steal a running run
    again = await c.post("/api/v1/runs/runner/claim", json={"runner_id": "chaos-2"}, headers=rh)
    assert again.status_code == 204
