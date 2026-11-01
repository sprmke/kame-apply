"""Phase 5: adapters, normalize, dedupe, discovery, directory, RLS."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

from app.companies.ats_detect import detect_ats_url
from app.companies.seed import seed_directory
from app.core.config import Settings
from app.jobs.dedupe import same_job
from app.jobs.normalize import normalize_raw, parse_remote_eligibility
from app.main import create_app
from kame_core.sources import get_adapter, list_adapters
from kame_core.sources.base import RawJob
from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_workspaces import signup

FIXTURES = Path(__file__).parent / "fixtures" / "sources"


@pytest.fixture
async def env_disc():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c, app


def test_at_least_ten_adapters_registered():
    keys = list_adapters()
    assert len(keys) >= 10
    for required in (
        "greenhouse",
        "lever",
        "ashby",
        "workable",
        "remotive",
        "remoteok",
        "himalayas",
        "arbeitnow",
        "jobicy",
        "muse",
        "career_jsonld",
    ):
        assert required in keys


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "key",
    [
        "greenhouse",
        "lever",
        "ashby",
        "workable",
        "remotive",
        "remoteok",
        "himalayas",
        "arbeitnow",
        "jobicy",
        "muse",
        "smartrecruiters",
        "recruitee",
        "career_jsonld",
    ],
)
async def test_adapter_fixtures_yield_jobs(key: str):
    adapter = get_adapter(key, fixture_dir=FIXTURES / key)
    params: dict = {}
    if key not in {
        "remotive",
        "remoteok",
        "himalayas",
        "arbeitnow",
        "jobicy",
        "muse",
        "career_jsonld",
    }:
        params = {"slug": "acme"}
    jobs = [j async for j in adapter.discover(params)]
    assert jobs
    assert all(isinstance(j, RawJob) for j in jobs)
    assert all(j.title and j.external_id for j in jobs)


def test_ats_detect_patterns():
    d = detect_ats_url("https://boards.greenhouse.io/stripe")
    assert d and d.ats == "greenhouse" and d.slug == "stripe"
    d = detect_ats_url("https://jobs.lever.co/spotify")
    assert d and d.ats == "lever"
    d = detect_ats_url("https://jobs.ashbyhq.com/linear")
    assert d and d.ats == "ashby"
    assert detect_ats_url("https://example.com/careers") is None


def test_remote_eligibility_patterns():
    mode, elig = parse_remote_eligibility(location="Remote - US only", remote_flag=True, text="")
    assert mode == "remote"
    assert elig.get("countries") == ["US"]
    mode, elig = parse_remote_eligibility(
        location="Remote (Anywhere)", remote_flag=True, text="worldwide"
    )
    assert elig.get("anywhere") is True
    mode, _ = parse_remote_eligibility(location="Berlin, Germany", remote_flag=False, text="")
    assert mode == "on_site"


def test_normalize_and_dedupe_pair():
    raw = RawJob(
        external_id="1",
        source_key="greenhouse",
        title="Senior Software Engineer",
        company_name="Acme",
        url="https://example.com/1",
        apply_url="https://boards.greenhouse.io/acme/jobs/1",
        description_text="Python FastAPI remote",
        location_text="Remote",
        remote=True,
        ats="greenhouse",
    )
    a = normalize_raw(raw)
    b = normalize_raw(
        RawJob(
            external_id="2",
            source_key="himalayas",
            title="Senior Software Engineer",
            company_name="Acme",
            url="https://himalayas.app/2",
            apply_url="https://himalayas.app/2",
            description_text="Python FastAPI remote worldwide",
            location_text="Remote",
            remote=True,
        )
    )
    assert same_job(
        company_a=a["company_name"],
        title_a=a["title"],
        simhash_a=a["simhash"],
        company_b=b["company_name"],
        title_b=b["title"],
        simhash_b=b["simhash"],
    )


def test_dedupe_precision_recall_on_labeled_pairs():
    labeled = Path(__file__).parent / "evals" / "fixtures" / "dedupe" / "pairs.jsonl"
    rows = [json.loads(line) for line in labeled.read_text().splitlines() if line.strip()]
    assert len(rows) >= 300
    tp = fp = fn = 0
    for row in rows:
        pred = same_job(
            company_a=row["a"]["company"],
            title_a=row["a"]["title"],
            simhash_a=row["a"]["simhash"],
            company_b=row["b"]["company"],
            title_b=row["b"]["title"],
            simhash_b=row["b"]["simhash"],
        )
        label = bool(row["same"])
        if pred and label:
            tp += 1
        elif pred and not label:
            fp += 1
        elif (not pred) and label:
            fn += 1
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    assert precision >= 0.98
    assert recall >= 0.90


async def _profile(c, me):
    h = me.h(me.personal)
    rows = (await c.get("/api/v1/profiles", headers=h)).json()
    if rows:
        return rows[0]
    r = await c.post("/api/v1/profiles", json={"display_name": "Me"}, headers=h)
    assert r.status_code == 201
    return r.json()


@pytest.mark.asyncio
async def test_directory_seed_and_discover_with_fixtures(env_disc):
    c, _app = env_disc
    # Seed directory as owner role
    engine = create_async_engine(TEST_OWNER_URL)
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        stats = await seed_directory(session, target_boards=5000)
        await session.commit()
        assert stats["boards"] >= 5000
    await engine.dispose()

    me = await signup(c)
    h = me.h(me.personal)
    p = await _profile(c, me)
    tr = await c.post(
        "/api/v1/tracks",
        json={
            "profile_id": p["id"],
            "name": "Software Engineer",
            "nl_text": "software engineer remote python",
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

    from app.sources import service as src_service

    orig = src_service.start_discovery

    async def wrapped(ctx, track_id, **kwargs):
        return await orig(ctx, track_id, fixture_root=FIXTURES, **kwargs)

    src_service.start_discovery = wrapped
    try:
        r = await c.post(f"/api/v1/tracks/{track_id}/discover", headers=h)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["status"] == "succeeded"
        assert body["progress"]["boards_checked"] >= 1
        jobs = await c.get(f"/api/v1/tracks/{track_id}/jobs", headers=h)
        assert jobs.status_code == 200
        health = await c.get("/api/v1/sources/health", headers=h)
        assert health.status_code == 200
        assert len(health.json()) >= 10
        stats = await c.get("/api/v1/sources/directory/stats", headers=h)
        assert stats.status_code == 200
        assert stats.json()["boards_active"] >= 5000
        add = await c.post(
            "/api/v1/sources/careers",
            json={"url": "https://boards.greenhouse.io/newco-phase5"},
            headers=h,
        )
        assert add.status_code == 201
        assert add.json()["ats"] == "greenhouse"
        sources = await c.get(f"/api/v1/tracks/{track_id}/sources", headers=h)
        assert sources.status_code == 200
        assert len(sources.json()) >= 1
    finally:
        src_service.start_discovery = orig


@pytest.mark.asyncio
async def test_track_jobs_cross_tenant_404(env_disc):
    c, _ = env_disc
    a = await signup(c)
    ha = a.h(a.personal)
    p = await _profile(c, a)
    tr = await c.post(
        "/api/v1/tracks",
        json={
            "profile_id": p["id"],
            "name": "X",
            "criteria": {
                "schema_version": 1,
                "titles": [{"title": "Engineer", "synonyms": [], "exclude": False}],
            },
        },
        headers=ha,
    )
    track_id = tr.json()["id"]
    b = await signup(c)
    hb = b.h(b.personal)
    r = await c.get(f"/api/v1/tracks/{track_id}/jobs", headers=hb)
    assert r.status_code == 404
