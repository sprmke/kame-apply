"""Phase 10: schedules, tick with frozen time, pause, prefs, RLS."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.rls import set_request_context
from app.main import create_app
from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_workspaces import signup

P = "/api/v1/profiles"
T = "/api/v1/tracks"


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


async def _track(c, me):
    h = me.h(me.personal)
    p = (await c.post(P, json={"display_name": "Sched User"}, headers=h)).json()
    track = (
        await c.post(
            T,
            json={
                "profile_id": p["id"],
                "name": "Sched Track",
                "nl_text": "python engineer",
                "criteria": {
                    "titles": [{"title": "Engineer", "synonyms": [], "exclude": False}],
                    "skills": {"must": ["Python"], "nice": [], "exclude": []},
                },
            },
            headers=h,
        )
    ).json()
    return h, track


@pytest.mark.asyncio
async def test_schedule_crud_and_tick(env_s):
    c = env_s
    me = await signup(c)
    h, track = await _track(c, me)
    tid = track["id"]

    created = await c.post(
        f"/api/v1/tracks/{tid}/schedules",
        json={
            "preset": "every_2_hours",
            "timezone": "Asia/Manila",
            "quiet_hours": {"start": "23:00", "end": "07:00"},
            "daily_cap": 6,
        },
        headers=h,
    )
    assert created.status_code == 201, created.text
    sched = created.json()
    assert "every 2 hours" in sched["preview"]
    assert sched["timezone"] == "Asia/Manila"
    assert sched["enabled"] is True
    assert sched["next_run_at"] is not None

    listed = await c.get(f"/api/v1/tracks/{tid}/schedules", headers=h)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    # Force due: set next_run_at in the past via owner
    engine = create_async_engine(TEST_OWNER_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            text("UPDATE schedules SET next_run_at = :t WHERE id = :id"),
            {"t": datetime.now(UTC) - timedelta(minutes=5), "id": sched["id"]},
        )
        await session.commit()
    await engine.dispose()

    # Midday Manila (not quiet hours): 2026-11-02 10:00 Manila = 02:00 UTC
    frozen = datetime(2026, 11, 2, 2, 0, tzinfo=UTC)
    tick = await c.post(
        "/api/v1/schedules/tick",
        json={"now": frozen.isoformat(), "workspace_only": True},
        headers=h,
    )
    assert tick.status_code == 200, tick.text
    body = tick.json()
    assert body["fired"] + body["skipped"] >= 1

    history = await c.get(f"/api/v1/tracks/{tid}/runs", headers=h)
    assert history.status_code == 200

    # Source-scoped schedule
    sources = await c.get(f"/api/v1/tracks/{tid}/sources", headers=h)
    assert sources.status_code == 200
    src_rows = sources.json()
    if src_rows:
        sid = src_rows[0]["source_id"]
        src_sched = await c.post(
            f"/api/v1/tracks/{tid}/schedules",
            json={
                "scope": "source",
                "source_id": sid,
                "preset": "hourly",
                "timezone": "Asia/Manila",
            },
            headers=h,
        )
        assert src_sched.status_code == 201, src_sched.text
        assert src_sched.json()["scope"] == "source"


@pytest.mark.asyncio
async def test_pause_stops_schedules(env_s):
    c = env_s
    me = await signup(c)
    h, track = await _track(c, me)
    tid = track["id"]
    await c.post(
        f"/api/v1/tracks/{tid}/schedules",
        json={"preset": "hourly", "timezone": "UTC"},
        headers=h,
    )
    paused = await c.post(f"/api/v1/tracks/{tid}/pause", headers=h)
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"
    rows = (await c.get(f"/api/v1/tracks/{tid}/schedules", headers=h)).json()
    assert all(not r["enabled"] for r in rows)

    resumed = await c.post(f"/api/v1/tracks/{tid}/resume", headers=h)
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "active"
    rows2 = (await c.get(f"/api/v1/tracks/{tid}/schedules", headers=h)).json()
    assert all(r["enabled"] for r in rows2)
    assert all(r["next_run_at"] for r in rows2)


@pytest.mark.asyncio
async def test_quiet_hours_skip(env_s):
    c = env_s
    me = await signup(c)
    h, track = await _track(c, me)
    tid = track["id"]
    created = (
        await c.post(
            f"/api/v1/tracks/{tid}/schedules",
            json={
                "preset": "hourly",
                "timezone": "Asia/Manila",
                "quiet_hours": {"start": "23:00", "end": "07:00"},
            },
            headers=h,
        )
    ).json()

    # 01:00 Manila = 17:00 previous day UTC. next_run_at must be <= frozen tick time.
    frozen = datetime(2026, 11, 1, 17, 0, tzinfo=UTC)
    engine = create_async_engine(TEST_OWNER_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            text("UPDATE schedules SET next_run_at = :t WHERE id = :id"),
            {"t": frozen - timedelta(minutes=1), "id": created["id"]},
        )
        await session.commit()
    await engine.dispose()

    tick = await c.post(
        "/api/v1/schedules/tick",
        json={"now": frozen.isoformat(), "workspace_only": True},
        headers=h,
    )
    assert tick.status_code == 200
    assert tick.json()["fired"] == 0
    assert any(d.get("skip") == "quiet_hours" for d in tick.json()["details"])


@pytest.mark.asyncio
async def test_notification_prefs_and_emit(env_s):
    c = env_s
    me = await signup(c)
    h = me.h(me.personal)

    prefs = await c.get("/api/v1/notification-prefs", headers=h)
    assert prefs.status_code == 200
    cells = prefs.json()["cells"]
    assert len(cells) == 24  # 4 channels x 6 events

    updated = await c.put(
        "/api/v1/notification-prefs",
        json={"cells": [{"channel": "email", "event": "digest", "enabled": False}]},
        headers=h,
    )
    assert updated.status_code == 200
    digest_email = next(
        x for x in updated.json()["cells"] if x["channel"] == "email" and x["event"] == "digest"
    )
    assert digest_email["enabled"] is False

    needs = await c.get("/api/v1/needs-you", headers=h)
    assert needs.status_code == 200
    assert "count" in needs.json()
    assert "items" in needs.json()

    # Empty list ok
    notes = await c.get("/api/v1/notifications", headers=h)
    assert notes.status_code == 200


@pytest.mark.asyncio
async def test_schedules_rls_wrong_workspace(env_s):
    c = env_s
    me = await signup(c)
    h, track = await _track(c, me)
    created = (
        await c.post(
            f"/api/v1/tracks/{track['id']}/schedules",
            json={"preset": "hourly", "timezone": "UTC"},
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
                text("SELECT count(*) FROM schedules WHERE id = :id"),
                {"id": created["id"]},
            )
        ).scalar_one()
        assert n == 0
    await engine.dispose()

    other = await signup(c)
    cross = await c.get(
        f"/api/v1/tracks/{track['id']}/schedules",
        headers=other.h(other.personal),
    )
    # Track not in other workspace → 404
    assert cross.status_code == 404
