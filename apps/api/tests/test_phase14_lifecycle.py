"""Phase 14: export, feedback, trusted proxy IP, R2 purge on delete."""

from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.core.mail import Outbox
from app.core.ratelimit import client_ip
from app.core.storage import MemoryStorage
from app.main import create_app
from tests.conftest import TEST_DB_URL
from tests.test_workspaces import signup, team_with


@pytest.fixture
async def env():
    settings = Settings(
        database_url=TEST_DB_URL,
        environment="test",
        log_json=False,
        auth_rate_limit_enabled=False,
        trusted_proxies="10.0.0.0/8",
    )
    app = create_app(settings)
    app.state.mailer = Outbox()
    storage = MemoryStorage()
    app.state.storage = storage
    async with app.router.lifespan_context(app):
        app.state.storage = storage
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c, app, storage


async def test_export_and_delete_purges_r2(env):
    c, app, storage = env
    owner = await signup(c)
    ws, _ = await team_with(c, owner, app.state.mailer, {})
    key = f"ws/{ws}/docs/resume.pdf"
    await storage.put(key, b"%PDF-1.4", "application/pdf")
    assert key in storage.objects

    exp = await c.get("/api/v1/workspace/export", headers=owner.h(ws))
    assert exp.status_code == 200, exp.text
    body = exp.json()
    assert body["workspace"]["id"] == ws
    assert "ai_credentials_meta" in body
    assert "omitted" in body["notes"]

    deleted = await c.delete("/api/v1/workspace", headers=owner.h(ws))
    assert deleted.status_code == 200, deleted.text
    assert key not in storage.objects


async def test_feedback_rejects_email_pii(env):
    c, _, _ = env
    me = await signup(c)
    r = await c.post(
        "/api/v1/feedback",
        headers=me.h(me.personal),
        json={"category": "bug", "message": "Broken page contact me at a@b.com please"},
    )
    assert r.status_code == 422

    dashed = await c.post(
        "/api/v1/feedback",
        headers=me.h(me.personal),
        json={"category": "bug", "message": "My id looks like 123-45-6789 somehow."},
    )
    assert dashed.status_code == 422

    ok = await c.post(
        "/api/v1/feedback",
        headers=me.h(me.personal),
        json={"category": "friction", "message": "Job list feels slow when filters change."},
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["ok"] is True


async def test_ops_dashboard_admin(env):
    c, _, _ = env
    owner = await signup(c)
    r = await c.get("/api/v1/ops/dashboard", headers=owner.h(owner.personal))
    assert r.status_code == 200, r.text
    data = r.json()
    assert "sources" in data and "ai_cost" in data and "recent_runs" in data


async def test_client_ip_trusts_proxy_header():
    settings = Settings(
        database_url=TEST_DB_URL,
        environment="test",
        log_json=False,
        auth_rate_limit_enabled=False,
        trusted_proxies="10.0.0.0/8",
    )
    fastapi_app = create_app(settings)

    req = SimpleNamespace(
        client=SimpleNamespace(host="10.1.2.3"),
        headers={"x-forwarded-for": "203.0.113.9, 10.1.2.3"},
        app=fastapi_app,
    )
    assert client_ip(req) == "203.0.113.9"  # type: ignore[arg-type]

    req2 = SimpleNamespace(
        client=SimpleNamespace(host="203.0.113.50"),
        headers={"x-forwarded-for": "1.2.3.4"},
        app=fastapi_app,
    )
    assert client_ip(req2) == "203.0.113.50"  # type: ignore[arg-type]
