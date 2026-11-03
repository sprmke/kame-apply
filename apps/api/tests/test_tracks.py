"""Tracks CRUD, criteria, RLS, and cross-tenant isolation."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.main import create_app
from app.taxonomy.seed import seed_taxonomy
from app.tracks.criteria import SkillSets, TitleSpec
from app.tracks.merge import CriteriaPatch
from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_ai import env  # noqa: F401
from tests.test_workspaces import signup

P = "/api/v1/profiles"
T = "/api/v1/tracks"


@pytest.fixture
async def env_tracks():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c, app


async def _profile(c, who):
    r = await c.post(P, json={"display_name": "Ana Reyes"}, headers=who.h(who.personal))
    assert r.status_code == 201, r.text
    return r.json()


def _criteria(**kw):
    base = {
        "titles": [{"title": "AI Engineer", "synonyms": [], "exclude": False}],
        "skills": {"must": ["Python"], "nice": [], "exclude": []},
    }
    base.update(kw)
    return base


@pytest.fixture
async def seeded_templates():
    engine = create_async_engine(TEST_OWNER_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        stats = await seed_taxonomy(session)
    await engine.dispose()
    assert stats["template_total"] >= 40
    return stats


async def test_create_list_update_archive_duplicate_reorder(env, seeded_templates):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await _profile(c, me)

    created = await c.post(
        T,
        json={
            "profile_id": p["id"],
            "name": "AI roles",
            "color_hue": 2,
            "criteria": _criteria(),
            "nl_text": "AI engineer, Python",
        },
        headers=h,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "AI roles"
    assert body["preview_message"].startswith("Preview available")
    assert body["criteria"]["version"] == 1
    assert "AI Engineer" in body["summary"]
    tid = body["id"]

    listed = (await c.get(T, headers=h)).json()
    assert [x["id"] for x in listed] == [tid]

    patched = await c.patch(T + f"/{tid}", json={"autonomy": "prepare"}, headers=h)
    assert patched.status_code == 200 and patched.json()["autonomy"] == "prepare"

    from_tmpl = await c.post(
        T,
        json={"profile_id": p["id"], "template_slug": "ai-engineer"},
        headers=h,
    )
    assert from_tmpl.status_code == 201, from_tmpl.text
    assert from_tmpl.json()["template_slug"] == "ai-engineer"

    dup = await c.post(T + f"/{tid}/duplicate", headers=h)
    assert dup.status_code == 201
    assert "copy" in dup.json()["name"].lower()

    ids = [r["id"] for r in (await c.get(T, headers=h)).json()]
    reordered = await c.post(T + "/reorder", json={"ordered_ids": list(reversed(ids))}, headers=h)
    assert reordered.status_code == 200
    assert [r["id"] for r in reordered.json()] == list(reversed(ids))

    archived = await c.post(T + f"/{tid}/archive", headers=h)
    assert archived.status_code == 200 and archived.json()["status"] == "archived"
    assert tid not in [r["id"] for r in (await c.get(T, headers=h)).json()]


async def test_put_criteria_increments_version(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await _profile(c, me)
    tid = (
        await c.post(
            T,
            json={
                "profile_id": p["id"],
                "name": "Nurse",
                "criteria": _criteria(
                    titles=[{"title": "Registered Nurse", "synonyms": [], "exclude": False}]
                ),
            },
            headers=h,
        )
    ).json()["id"]
    r = await c.put(
        T + f"/{tid}/criteria",
        json={
            "criteria": _criteria(
                titles=[{"title": "ICU Nurse", "synonyms": [], "exclude": False}],
                visa_sponsorship=True,
            ),
            "nl_text": "ICU nurse, visa sponsorship",
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["criteria"]["version"] == 2
    assert r.json()["criteria"]["structured"]["visa_sponsorship"] is True


async def test_compile_preview_with_injected_runner(env_tracks):
    c, app = env_tracks
    me = await signup(c)
    h = me.h(me.personal)
    p = await _profile(c, me)
    tid = (
        await c.post(
            T,
            json={
                "profile_id": p["id"],
                "name": "Backend",
                "criteria": _criteria(
                    titles=[{"title": "Backend Engineer", "synonyms": [], "exclude": False}]
                ),
            },
            headers=h,
        )
    ).json()["id"]

    class Result:
        output = CriteriaPatch(
            titles=[TitleSpec(title="Platform Engineer")],
            companies={"exclude_agencies": True},
            skills=SkillSets(must=[], nice=[], exclude=["Angular"]),
        )
        provider = "test"
        model = "test"

    async def fake_runner(ctx, settings, **kwargs):
        assert kwargs["feature"] == "criteria_compile"
        return Result()

    app.state.run_structured = fake_runner
    r = await c.post(
        T + f"/{tid}/criteria/compile",
        json={"text": "also platform engineer, exclude Angular, no agencies", "apply": False},
        headers=h,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["summary"]
    assert any(d.get("path") for d in data["diff"])


async def test_templates_list(env, seeded_templates):  # noqa: F811
    c, _ = env
    me = await signup(c)
    r = await c.get(T + "/templates", headers=me.h(me.personal))
    assert r.status_code == 200
    assert len(r.json()) >= 40


async def test_cross_tenant_track_is_404(env):  # noqa: F811
    c, _ = env
    a = await signup(c)
    b = await signup(c)
    pa = await _profile(c, a)
    tid = (
        await c.post(
            T,
            json={"profile_id": pa["id"], "name": "Secret", "criteria": _criteria()},
            headers=a.h(a.personal),
        )
    ).json()["id"]
    r = await c.get(T + f"/{tid}", headers=b.h(b.personal))
    assert r.status_code == 404


async def test_tracks_rls_wrong_workspace_returns_zero_rows(env, tenancy):  # noqa: F811
    """Raw SQL with wrong app.workspace_id sees 0 track rows."""
    c, _ = env
    me = await signup(c)
    p = await _profile(c, me)
    tid = (
        await c.post(
            T,
            json={"profile_id": p["id"], "name": "RLS", "criteria": _criteria()},
            headers=me.h(me.personal),
        )
    ).json()["id"]

    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.execute(
            text("SELECT set_config('app.workspace_id', :w, true)"),
            {"w": str(tenancy.ws_b)},
        )
        await conn.execute(
            text("SELECT set_config('app.user_id', :u, true)"),
            {"u": str(tenancy.users["b_owner"])},
        )
        n = (
            await conn.execute(text("SELECT count(*) FROM tracks WHERE id = :id"), {"id": tid})
        ).scalar_one()
        assert n == 0
    await engine.dispose()


async def test_skill_normalize_alias(env, seeded_templates):  # noqa: F811
    c, _ = env
    me = await signup(c)
    r = await c.get(
        "/api/v1/taxonomy/skills/normalize", params={"q": "k8s"}, headers=me.h(me.personal)
    )
    assert r.status_code == 200
    assert r.json()["canonical"] == "Kubernetes"


@pytest.mark.asyncio
async def test_duplicate_carries_source_choices_and_settings(env, seeded_templates):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await _profile(c, me)
    track = await c.post(
        T,
        json={"profile_id": p["id"], "name": "Sourceful", "criteria": _criteria()},
        headers=h,
    )
    assert track.status_code == 201, track.text
    tid = track.json()["id"]
    from app.companies.seed import seed_sources

    engine = create_async_engine(TEST_OWNER_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await seed_sources(session)
        await session.commit()
    await engine.dispose()
    sources = (await c.get(f"{T}/{tid}/sources", headers=h)).json()
    assert sources
    source_id = sources[0]["source_id"]
    patched = await c.patch(f"{T}/{tid}/sources/{source_id}", json={"enabled": False}, headers=h)
    assert patched.status_code == 200, patched.text
    updated = await c.patch(f"{T}/{tid}", json={"settings": {"min_score": 0.75}}, headers=h)
    assert updated.status_code == 200, updated.text

    dup = await c.post(f"{T}/{tid}/duplicate", headers=h)
    assert dup.status_code == 201, dup.text
    new_id = dup.json()["id"]
    new_sources = (await c.get(f"{T}/{new_id}/sources", headers=h)).json()
    by_source = {row["source_id"]: row for row in new_sources}
    assert by_source[source_id]["enabled"] is False
    new_track = (await c.get(f"{T}/{new_id}", headers=h)).json()
    assert new_track["settings"] == {"min_score": 0.75}
