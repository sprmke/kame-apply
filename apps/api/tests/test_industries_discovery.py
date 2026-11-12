"""IND-4: classification, query planning, search adapters, cache, coverage, alerts."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.industries.registry import require_pack
from app.jobs.classify import classify_job
from app.sources.search_service import _cached, _hash, _store_cache, plan_queries
from app.tracks.criteria import CriteriaV1, LocationFilter, TitleSpec
from app.tracks.models import Track
from kame_core.sources import get_adapter
from tests.conftest import TEST_DB_URL
from tests.test_ai import env  # noqa: F401
from tests.test_workspaces import signup

FIXTURES = Path(__file__).parent / "fixtures" / "sources"


def test_classify_chef_and_not_server_engineer():
    chef = classify_job(
        "Sous Chef",
        "Hotel kitchen, HACCP, evening and weekend shifts, Filipino cuisine, 180 covers.",
    )
    assert chef.industry_hints == ["hospitality"]
    assert chef.occupation_code == "34"
    assert "hotel" in chef.facets["kitchen_type"]
    assert "filipino" in chef.facets["cuisine"]
    assert "evening" in chef.facets["shifts"]
    assert "haccp" in chef.facets["credentials"]

    backend = classify_job("Server Engineer", "Python, Kubernetes, API, remote")
    assert "hospitality" not in backend.industry_hints
    assert "technology" in backend.industry_hints


def test_plan_queries_uses_titles_and_locations_only():
    track = Track(name="Sous chef Dubai", industry="hospitality")
    criteria = CriteriaV1(
        titles=[TitleSpec(title="Sous chef"), TitleSpec(title="Chef de partie")],
        locations=[LocationFilter(place="Dubai", country="AE", radius_km=20)],
        posting_max_age_days=21,
    )
    queries = plan_queries(track, criteria, require_pack("hospitality"), limit=6)
    assert len(queries) == 2
    assert {q["keywords"] for q in queries} == {"Sous chef", "Chef de partie"}
    assert all(q["location"] == "Dubai" and q["country"] == "AE" for q in queries)
    assert all(q["posted_within_days"] == 21 for q in queries)


async def test_search_adapter_fixtures_yield_jobs():
    jooble = get_adapter("search_jooble", fixture_dir=FIXTURES / "search_jooble")
    jobs = [
        job
        async for job in jooble.discover(
            {"keywords": "Sous chef", "location": "Dubai", "country": "AE"}
        )
    ]
    assert [job.title for job in jobs] == ["Sous Chef", "Commis Chef"]
    assert all(job.source_key == "search_jooble" for job in jobs)
    assert jobs[0].salary_min is not None

    adzuna = get_adapter("search_adzuna", fixture_dir=FIXTURES / "search_adzuna")
    adzuna_jobs = [
        job
        async for job in adzuna.discover(
            {"keywords": "Head chef", "location": "London", "country": "GB"}
        )
    ]
    assert [job.title for job in adzuna_jobs] == ["Head Chef"]
    assert adzuna_jobs[0].company_name == "Riverside Kitchen"


async def test_query_cache_round_trip_and_expiry():
    engine = create_async_engine(TEST_DB_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    now = datetime.now(UTC)
    query = {"keywords": "cache-test", "location": "Dubai", "country": "AE"}
    key = _hash(query)
    async with factory() as session:
        await _store_cache(session, "search_jooble", key, [{"title": "x"}], ttl_hours=1, now=now)
        await session.commit()
        hit = await _cached(session, "search_jooble", key, now)
        assert hit == [{"title": "x"}]
    await engine.dispose()


async def test_where_and_coverage_and_alert_guides(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    assert (
        await c.post("/api/v1/workspace/industries", json={"key": "hospitality"}, headers=h)
    ).status_code == 200
    profile = (await c.post("/api/v1/profiles", json={"display_name": "Ana"}, headers=h)).json()
    created = await c.post(
        "/api/v1/tracks",
        json={
            "profile_id": profile["id"],
            "name": "Sous chef Dubai",
            "industry": "hospitality",
            "criteria": {
                "titles": [{"title": "Sous chef", "synonyms": [], "exclude": False}],
                "locations": [{"place": "Dubai", "country": "AE", "radius_km": 20}],
            },
        },
        headers=h,
    )
    assert created.status_code == 201, created.text
    track_id = created.json()["id"]

    where = await c.get(f"/api/v1/tracks/{track_id}/where", headers=h)
    assert where.status_code == 200, where.text
    body = where.json()
    assert body["queries"][0]["keywords"] == "Sous chef"
    assert body["queries"][0]["country"] == "AE"
    keys = {adapter["key"] for adapter in body["adapters"]}
    assert {"search_jooble", "search_adzuna"} <= keys
    assert all(adapter["configured"] is False for adapter in body["adapters"])

    coverage = await c.get(
        "/api/v1/sources/coverage",
        params={"industry": "hospitality", "country": "AE"},
        headers=h,
    )
    assert coverage.status_code == 200, coverage.text
    assert coverage.json()["level"] == "partial"
    assert coverage.json()["sources"]

    guides = await c.get(
        "/api/v1/sources/alerts/guide",
        params={
            "industry": "hospitality",
            "country": "AE",
            "q": "Sous chef",
            "location": "Dubai",
        },
        headers=h,
    )
    assert guides.status_code == 200, guides.text
    providers = {item["provider"] for item in guides.json()}
    assert {"indeed", "linkedin", "culinary_agents"} <= providers


async def test_hospitality_search_run_ingests_and_links_chef_jobs(env, tmp_path):  # noqa: F811
    import shutil

    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.companies.seed import seed_sources
    from app.core.rls import set_request_context
    from app.core.security import WorkspaceContext
    from app.jobs.models import Job, TrackJob
    from app.sources.discover import run_discover_track
    from app.sources.models import Source, TrackSource
    from tests.conftest import TEST_DB_URL

    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    assert (
        await c.post("/api/v1/workspace/industries", json={"key": "hospitality"}, headers=h)
    ).status_code == 200
    profile = (await c.post("/api/v1/profiles", json={"display_name": "Ana"}, headers=h)).json()
    track = await c.post(
        "/api/v1/tracks",
        json={
            "profile_id": profile["id"],
            "name": "Sous chef Dubai",
            "industry": "hospitality",
            "criteria": {
                "titles": [{"title": "Sous chef", "synonyms": [], "exclude": False}],
                "locations": [{"place": "Dubai", "country": "AE", "radius_km": 20}],
            },
        },
        headers=h,
    )
    assert track.status_code == 201, track.text
    track_id = track.json()["id"]

    root = tmp_path / "sources"
    (root / "search_jooble").mkdir(parents=True)
    shutil.copy(FIXTURES / "search_jooble" / "jobs.json", root / "search_jooble" / "jobs.json")

    engine = create_async_engine(TEST_DB_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await set_request_context(session, user_id=me.id, workspace_id=me.personal)
        await seed_sources(session)
        source = (
            await session.execute(select(Source).where(Source.key == "search_jooble"))
        ).scalar_one()
        session.add(
            TrackSource(
                workspace_id=uuid.UUID(me.personal),
                track_id=uuid.UUID(track_id),
                source_id=source.id,
                enabled=True,
            )
        )
        await session.commit()
        await set_request_context(session, user_id=me.id, workspace_id=me.personal)
        ctx = WorkspaceContext(
            session=session,
            user_id=uuid.UUID(me.id),
            workspace_id=uuid.UUID(me.personal),
            role="owner",
            request_id=None,
        )
        run = await run_discover_track(ctx, uuid.UUID(track_id), fixture_root=root, board_limit=0)
        await session.commit()
        await set_request_context(session, user_id=me.id, workspace_id=me.personal)
        assert run.status == "succeeded", run.error
        assert run.progress["jobs_new"] >= 2
        assert run.progress["linked"] >= 1
        rows = (
            await session.execute(
                select(Job, TrackJob)
                .join(TrackJob, TrackJob.job_id == Job.id)
                .where(TrackJob.track_id == uuid.UUID(track_id))
            )
        ).all()
        assert rows, (run.status, run.progress)
        titles = {job.title for job, _ in rows}
        assert "Sous Chef" in titles
        assert all("hospitality" in (job.industry_hints or []) for job, _ in rows)
        assert any((job.facets or {}).get("credentials") for job, _ in rows)
    await engine.dispose()
