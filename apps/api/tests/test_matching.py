"""Phase 6 API: score, board, triage, CSV, relaxations, cross-tenant."""

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


@pytest.fixture
async def env_m():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c


async def _profile(c: AsyncClient, me) -> dict:
    r = await c.get("/api/v1/profiles", headers=me.h(me.personal))
    assert r.status_code == 200
    rows = r.json()
    if rows:
        return rows[0]
    r = await c.post(
        "/api/v1/profiles",
        json={"display_name": "Pat", "headline": "Engineer"},
        headers=me.h(me.personal),
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _seed_job_and_track(c: AsyncClient, me) -> tuple[str, str, str]:
    h = me.h(me.personal)
    p = await _profile(c, me)
    tr = await c.post(
        "/api/v1/tracks",
        json={
            "profile_id": p["id"],
            "name": "Software Engineer",
            "nl_text": "software engineer remote Python",
            "criteria": {
                "schema_version": 1,
                "titles": [{"title": "Software Engineer", "synonyms": [], "exclude": False}],
                "skills": {"must": ["Python"], "nice": [], "exclude": []},
                "work_modes": ["remote"],
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
        job = Job(
            title="Senior Software Engineer",
            normalized_title="senior software engineer",
            skills=["Python", "FastAPI"],
            description_text=(
                "Requirements:\n- 5+ years of Python experience\n"
                "- Must be based in the US\n- Remote OK\n"
            ),
            description_html="<p>Python</p>",
            content_hash=f"h-{uuid.uuid4().hex}",
            simhash=1,
            canonical_url="https://example.com/jobs/1",
            apply_url="https://boards.greenhouse.io/acme/jobs/1",
            work_mode="remote",
            seniority="senior",
            remote_eligibility={"anywhere": False, "countries": ["US"]},
            salary={"min": 5000, "currency": "USD", "period": "month"},
            status="open",
        )
        session.add(job)
        await session.flush()
        tj = TrackJob(
            workspace_id=uuid.UUID(str(me.personal)),
            track_id=uuid.UUID(track_id),
            job_id=job.id,
            status="new",
            eligibility="unknown",
        )
        session.add(tj)
        await session.commit()
        job_id = str(job.id)
        tj_id = str(tj.id)
    await engine.dispose()
    return track_id, job_id, tj_id


@pytest.mark.asyncio
async def test_score_board_triage_csv_relax(env_m):
    c = env_m
    me = await signup(c)
    h = me.h(me.personal)
    track_id, _job_id, tj_id = await _seed_job_and_track(c, me)

    score = await c.post(f"/api/v1/tracks/{track_id}/score", headers=h)
    assert score.status_code == 200, score.text
    assert score.json()["scored"] >= 1

    board = await c.get(f"/api/v1/jobs?track_id={track_id}&include_not_eligible=true", headers=h)
    assert board.status_code == 200, board.text
    rows = board.json()
    assert rows
    assert "score" in rows[0]
    assert "reasons" in rows[0]

    detail = await c.get(f"/api/v1/track-jobs/{tj_id}", headers=h)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["qualifications"]
    assert body["title"]

    tri = await c.post(
        f"/api/v1/track-jobs/{tj_id}/triage",
        json={"action": "skip", "skip_reason": "too junior"},
        headers=h,
    )
    assert tri.status_code == 200, tri.text

    # Feedback learning: score again should still return
    score2 = await c.post(f"/api/v1/tracks/{track_id}/score", headers=h)
    assert score2.status_code == 200

    csv_r = await c.get(
        f"/api/v1/jobs/export.csv?track_id={track_id}&include_not_eligible=true", headers=h
    )
    assert csv_r.status_code == 200
    assert "title" in csv_r.text
    assert "score" in csv_r.text

    rel = await c.get(f"/api/v1/tracks/{track_id}/relaxations", headers=h)
    assert rel.status_code == 200


@pytest.mark.asyncio
async def test_track_job_cross_tenant_404(env_m):
    c = env_m
    a = await signup(c)
    _track_id, _job_id, tj_id = await _seed_job_and_track(c, a)
    b = await signup(c)
    r = await c.get(f"/api/v1/track-jobs/{tj_id}", headers=b.h(b.personal))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_job_qualifications_wrong_workspace_invisible():
    """Global quals exist; tenant track_jobs still RLS-scoped (0 rows wrong ws)."""
    engine = create_async_engine(TEST_DB_URL)
    async with engine.connect() as conn:
        await conn.execute(
            text("SELECT set_config('app.workspace_id', :w, false)"), {"w": str(uuid.uuid4())}
        )
        n = (await conn.execute(text("SELECT count(*) FROM track_jobs"))).scalar()
        assert n == 0
    await engine.dispose()
