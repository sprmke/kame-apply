"""Phase 16: live-view tokens, control takeover/handback, hub, input mapping, RLS."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.main import create_app
from app.runs.live_hub import LiveHub
from app.runs.live_tokens import decode_live_token, issue_live_token
from runner.live import map_pointer_to_page
from tests.conftest import TEST_DB_URL
from tests.test_phase15_runs import _seed_ready_application
from tests.test_workspaces import signup


@pytest.fixture
async def env_l():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c, settings


def test_map_pointer_to_page():
    x, y = map_pointer_to_page(
        canvas_x=100, canvas_y=50, canvas_w=200, canvas_h=100, page_w=1280, page_h=720
    )
    assert abs(x - 640) < 0.01
    assert abs(y - 360) < 0.01


def test_live_token_roundtrip():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    rid, wid, uid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    raw, exp = issue_live_token(settings, run_id=rid, workspace_id=wid, user_id=uid, role="viewer")
    claims = decode_live_token(settings, raw)
    assert claims["run_id"] == rid
    assert claims["workspace_id"] == wid
    assert claims["role"] == "viewer"
    assert exp.tzinfo is not None


@pytest.mark.asyncio
async def test_hub_controller_disconnect_pauses():
    hub = LiveHub()
    rid, wid = uuid.uuid4(), uuid.uuid4()
    room = await hub.room(rid, wid)
    room.control_mode = "human"
    room.controller_user_id = uuid.uuid4()

    class FakeWs:
        def __init__(self):
            self.closed = False
            self.sent = []

        async def send_json(self, msg):
            self.sent.append(msg)

        async def close(self, code=1000):
            self.closed = True

    from app.runs.live_hub import LivePeer

    controller = uuid.uuid4()
    room.controller_user_id = controller
    room.control_mode = "human"
    ws = FakeWs()
    room.viewers.append(LivePeer(ws=ws, role="viewer", user_id=controller))  # type: ignore[arg-type]
    await hub.leave(room, ws)  # type: ignore[arg-type]
    assert room.control_mode == "paused"
    assert room.controller_user_id is None


@pytest.mark.asyncio
async def test_live_token_takeover_handback(env_l):
    c, settings = env_l
    me = await signup(c)
    h, app_id, _ = await _seed_ready_application(
        c, me, apply_url="https://boards.greenhouse.io/acme/jobs/lv"
    )
    started = await c.post(
        "/api/v1/runs/runner/start",
        json={"application_id": app_id, "allow_submit": False},
        headers=h,
    )
    assert started.status_code == 201, started.text
    run_id = started.json()["id"]

    tok = await c.post(f"/api/v1/runs/{run_id}/live/token", headers=h)
    assert tok.status_code == 200, tok.text
    body = tok.json()
    assert body["role"] == "viewer"
    assert body["ws_path"].endswith(f"/runs/{run_id}/live")
    claims = decode_live_token(settings, body["token"])
    assert str(claims["run_id"]) == run_id

    state = await c.get(f"/api/v1/runs/{run_id}/live/state", headers=h)
    assert state.status_code == 200
    assert state.json()["control_mode"] == "agent"

    take = await c.post(f"/api/v1/runs/{run_id}/live/takeover", headers=h)
    assert take.status_code == 200, take.text
    assert take.json()["control_mode"] == "human"
    assert take.json()["controller_user_id"] == me.id
    assert take.json()["live_mode"] in {"screencast", "screenshot"}

    back = await c.post(f"/api/v1/runs/{run_id}/live/handback", headers=h)
    assert back.status_code == 200
    assert back.json()["control_mode"] == "agent"
    assert back.json()["controller_user_id"] is None

    mode = await c.patch(
        f"/api/v1/runs/{run_id}/live/mode",
        json={"live_mode": "screenshot"},
        headers=h,
    )
    assert mode.status_code == 200
    assert mode.json()["live_mode"] == "screenshot"


@pytest.mark.asyncio
async def test_checkpoint_switches_to_human(env_l):
    c, _settings = env_l
    me = await signup(c)
    h, app_id, _ = await _seed_ready_application(c, me, apply_url="https://jobs.lever.co/acme/lv")
    tok = await c.post("/api/v1/runs/tokens", json={"label": "cloud", "mode": "cloud"}, headers=h)
    raw = tok.json()["token"]
    rh = {"Authorization": f"Bearer {raw}", "X-Workspace-Id": str(me.personal)}
    started = await c.post(
        "/api/v1/runs/runner/start",
        json={"application_id": app_id, "allow_submit": False},
        headers=h,
    )
    run_id = started.json()["id"]
    await c.post("/api/v1/runs/runner/claim", json={"runner_id": "lv-1"}, headers=rh)
    cp = await c.post(
        f"/api/v1/runs/{run_id}/checkpoints",
        json={"kind": "captcha", "detail": {"message": "Solve"}},
        headers=rh,
    )
    assert cp.status_code == 201
    got = await c.get(f"/api/v1/runs/{run_id}", headers=rh)
    assert got.json()["control_mode"] == "human"
    assert got.json()["live_mode"] == "screencast"


@pytest.mark.asyncio
async def test_live_cross_tenant_404(env_l):
    c, _ = env_l
    a = await signup(c)
    b = await signup(c)
    ah, app_id, _ = await _seed_ready_application(
        c, a, apply_url="https://jobs.ashbyhq.com/acme/lv"
    )
    started = await c.post(
        "/api/v1/runs/runner/start",
        json={"application_id": app_id, "allow_submit": False},
        headers=ah,
    )
    run_id = started.json()["id"]
    bh = b.h(b.personal)
    assert (await c.post(f"/api/v1/runs/{run_id}/live/token", headers=bh)).status_code == 404
    assert (await c.post(f"/api/v1/runs/{run_id}/live/takeover", headers=bh)).status_code == 404


@pytest.mark.asyncio
async def test_field_lock(env_l):
    c, _ = env_l
    me = await signup(c)
    h, app_id, _ = await _seed_ready_application(
        c, me, apply_url="https://boards.greenhouse.io/acme/lock"
    )
    tok = await c.post("/api/v1/runs/tokens", json={"label": "cloud", "mode": "cloud"}, headers=h)
    rh = {
        "Authorization": f"Bearer {tok.json()['token']}",
        "X-Workspace-Id": str(me.personal),
    }
    started = await c.post(
        "/api/v1/runs/runner/start",
        json={"application_id": app_id, "allow_submit": False},
        headers=h,
    )
    run_id = started.json()["id"]
    await c.post("/api/v1/runs/runner/claim", json={"runner_id": "lv-2"}, headers=rh)
    lock = await c.post(
        f"/api/v1/runs/{run_id}/live/field-lock",
        json={"field_id": "email#0", "label": "Email"},
        headers=rh,
    )
    assert lock.status_code == 200
    got = await c.get(f"/api/v1/runs/{run_id}", headers=rh)
    fields = got.json()["user_edited_fields"]
    assert any(f.get("field_id") == "email#0" for f in fields)
