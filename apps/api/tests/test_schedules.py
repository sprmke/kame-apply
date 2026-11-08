"""Phase 10: schedules, tick with frozen time, pause, prefs, RLS."""

from __future__ import annotations

import uuid
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


@pytest.fixture
async def env_scheduler():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c, app


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
async def test_schedule_crud_and_tick(env_s, monkeypatch):
    from types import SimpleNamespace

    from app.schedules import chain

    async def fake_chain(ctx, track_id, **kwargs):
        return SimpleNamespace(id=uuid.uuid4(), status="succeeded")

    monkeypatch.setattr(chain, "run_automation_chain", fake_chain)
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
    frozen = datetime.now(UTC).replace(second=0, microsecond=0) + timedelta(hours=1)
    async with factory() as session:
        await session.execute(
            text("UPDATE schedules SET next_run_at = :t WHERE id = :id"),
            {"t": frozen - timedelta(minutes=5), "id": sched["id"]},
        )
        await session.commit()
    await engine.dispose()

    # A due schedule fires once at the frozen time (derived from now, so the test cannot rot).
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

    # The matrix exposes push/telegram; saving those cells must not hit a check constraint.
    push_cells = await c.put(
        "/api/v1/notification-prefs",
        json={
            "cells": [
                {"channel": "push", "event": "needs_review", "enabled": True},
                {"channel": "telegram", "event": "risk_flag", "enabled": True},
            ]
        },
        headers=h,
    )
    assert push_cells.status_code == 200, push_cells.text
    saved = {(x["channel"], x["event"]): x["enabled"] for x in push_cells.json()["cells"]}
    assert saved[("push", "needs_review")] is True
    assert saved[("telegram", "risk_flag")] is True

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


@pytest.mark.asyncio
async def test_two_active_runs_do_not_break_the_tick(env_s):
    """Two concurrent runs used to raise MultipleResultsFound and skip every cycle."""
    c = env_s
    me = await signup(c)
    h, track = await _track(c, me)
    tid = track["id"]
    await c.post(
        f"/api/v1/tracks/{tid}/schedules",
        json={"preset": "hourly", "timezone": "UTC"},
        headers=h,
    )
    frozen = datetime.now(UTC).replace(second=0, microsecond=0) + timedelta(hours=1)
    engine = create_async_engine(TEST_OWNER_URL)
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE schedules SET next_run_at = :t WHERE track_id = :tid"),
            {"t": frozen - timedelta(minutes=5), "tid": tid},
        )
        for _ in range(2):
            await conn.execute(
                text(
                    "INSERT INTO discovery_runs (workspace_id, track_id, status, trigger, progress) "
                    "VALUES (:w, :t, 'queued', 'schedule', '{}')"
                ),
                {"w": me.personal, "t": tid},
            )
    await engine.dispose()

    tick = await c.post(
        "/api/v1/schedules/tick",
        json={"now": frozen.isoformat(), "workspace_only": True},
        headers=h,
    )
    assert tick.status_code == 200, tick.text
    assert any(d.get("skip") == "previous_run_still_active" for d in tick.json().get("details", []))


@pytest.mark.asyncio
async def test_scheduler_runs_due_schedules_for_every_workspace(env_scheduler, monkeypatch):
    """The in-process scheduler must reach every tenant, which needs the security-definer helper."""
    from types import SimpleNamespace

    from app.schedules import chain
    from app.schedules.scheduler import run_once

    c, app = env_scheduler
    ids = []
    for _ in range(2):
        me = await signup(c)
        h, track = await _track(c, me)
        await c.post(
            f"/api/v1/tracks/{track['id']}/schedules",
            json={"preset": "hourly", "timezone": "UTC"},
            headers=h,
        )
        ids.append((me.personal, track["id"]))

    frozen = datetime.now(UTC).replace(second=0, microsecond=0) + timedelta(hours=1)
    engine = create_async_engine(TEST_OWNER_URL)
    async with engine.begin() as conn:
        for ws, tid in ids:
            await conn.execute(
                text(
                    "UPDATE schedules SET next_run_at = :t "
                    "WHERE workspace_id = CAST(:w AS uuid) AND track_id = CAST(:tid AS uuid)"
                ),
                {"t": frozen - timedelta(minutes=5), "w": ws, "tid": tid},
            )
    await engine.dispose()

    calls: list[str] = []

    async def fake_chain(ctx, track_id, **kwargs):
        calls.append(str(track_id))
        return SimpleNamespace(id=uuid.uuid4(), status="succeeded")

    monkeypatch.setattr(chain, "run_automation_chain", fake_chain)
    result = await run_once(app, now=frozen)
    # The scheduler sees every workspace in the database, including ones from other tests.
    assert result["workspaces"] >= 2
    assert set(calls) >= {tid for _ws, tid in ids}
    assert result["fired"] >= 2


@pytest.mark.asyncio
async def test_scheduler_tick_takes_a_lock(env_scheduler):
    """A second worker must skip the tick rather than double-fire schedules."""
    from app.schedules.scheduler import SCHEDULER_LOCK_KEY, run_once

    _c, app = env_scheduler
    async with app.state.session_factory() as holder:
        await holder.execute(text("SELECT pg_advisory_lock(:k)"), {"k": SCHEDULER_LOCK_KEY})
        try:
            result = await run_once(app)
            assert result.get("skipped_lock") == 1
        finally:
            await holder.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": SCHEDULER_LOCK_KEY})
