"""Phase 17: email parsers, inbound webhook, push/telegram link, RLS."""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.ingest.parsers import detect_provider, parse_mime, unwrap_tracking_url
from app.main import create_app
from tests.conftest import TEST_DB_URL
from tests.test_workspaces import signup

FIXTURES = Path(__file__).parent / "fixtures" / "email_alerts"


@pytest.fixture
async def env_i():
    settings = Settings(
        database_url=TEST_DB_URL,
        environment="test",
        log_json=False,
        auth_rate_limit_enabled=False,
        inbound_webhook_secret="test-webhook-secret",
        inbound_email_domain="in.kameapply.test",
        telegram_bot_username="kame_test_bot",
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c, settings


def test_unwrap_tracking():
    u = unwrap_tracking_url(
        "https://www.google.com/url?q=https%3A%2F%2Fboards.greenhouse.io%2Facme%2Fjobs%2F1"
    )
    assert "greenhouse.io" in u


def test_detect_providers():
    assert detect_provider("jobalerts@linkedin.com", "jobs") == "linkedin"
    assert detect_provider("alert@indeed.com", "x") == "indeed"
    assert detect_provider("noreply@jobstreet.com", "x") == "jobstreet"


def test_parse_linkedin_fixture():
    raw = (FIXTURES / "linkedin.eml").read_bytes()
    result = parse_mime(raw)
    assert result.provider == "linkedin"
    assert len(result.jobs) >= 1
    assert result.jobs[0].url.startswith("http")
    assert result.confidence >= 0.5


def test_parse_indeed_and_jobstreet():
    for name in ("indeed.eml", "jobstreet.eml"):
        result = parse_mime((FIXTURES / name).read_bytes())
        assert result.jobs, name
        assert result.confidence >= 0.5


def test_forward_confirm():
    result = parse_mime((FIXTURES / "forward_confirm.eml").read_bytes())
    assert result.kind == "forward_confirm"
    assert result.jobs == []


@pytest.mark.asyncio
async def test_address_rotate_and_webhook(env_i):
    c, settings = env_i
    me = await signup(c)
    h = me.h(me.personal)

    addr = await c.get("/api/v1/inbound/address", headers=h)
    assert addr.status_code == 200, addr.text
    assert addr.json()["address"].startswith("alerts+")
    assert addr.json()["address"].endswith("@in.kameapply.test")
    token = addr.json()["address"].split("alerts+")[1].split("@")[0]

    guides = await c.get("/api/v1/inbound/guides", headers=h)
    assert guides.status_code == 200
    assert len(guides.json()) >= 2

    raw = (FIXTURES / "linkedin.eml").read_bytes()
    sig = hmac.new(settings.inbound_webhook_secret.encode(), raw, hashlib.sha256).hexdigest()
    wh = await c.post(
        f"/api/v1/webhooks/inbound-email?token={token}&from=linkedin&subject=jobs",
        content=raw,
        headers={"X-Kame-Signature": f"sha256={sig}"},
    )
    assert wh.status_code == 200, wh.text
    assert wh.json()["ok"] is True
    assert wh.json()["jobs_created"] >= 1 or wh.json()["status"] in {
        "parsed",
        "needs_review",
    }

    msgs = await c.get("/api/v1/inbound/messages", headers=h)
    assert msgs.status_code == 200
    assert len(msgs.json()) >= 1

    rotated = await c.post("/api/v1/inbound/address/rotate", headers=h)
    assert rotated.status_code == 200
    assert "alerts+" in rotated.json()["address"]
    assert rotated.json()["address"] != addr.json()["address"]


@pytest.mark.asyncio
async def test_webhook_bad_signature(env_i):
    c, _ = env_i
    me = await signup(c)
    h = me.h(me.personal)
    addr = (await c.get("/api/v1/inbound/address", headers=h)).json()
    token = addr["address"].split("alerts+")[1].split("@")[0]
    bad = await c.post(
        f"/api/v1/webhooks/inbound-email?token={token}",
        content=b"hello",
        headers={"X-Kame-Signature": "sha256=deadbeef"},
    )
    assert bad.status_code == 401


@pytest.mark.asyncio
async def test_push_subscribe_and_telegram_link(env_i):
    c, _ = env_i
    me = await signup(c)
    h = me.h(me.personal)

    sub = await c.post(
        "/api/v1/push/subscriptions",
        json={
            "endpoint": "https://push.example/sub/1",
            "p256dh": "BNcRd" + "x" * 20,
            "auth": "authsecret12",
            "user_agent": "test",
        },
        headers=h,
    )
    assert sub.status_code == 201, sub.text
    listed = await c.get("/api/v1/push/subscriptions", headers=h)
    assert len(listed.json()) == 1

    tg = await c.post("/api/v1/telegram/link", headers=h)
    assert tg.status_code == 200, tg.text
    assert tg.json()["link_code"]
    code = tg.json()["link_code"]

    # Simulate Telegram /start CODE
    wh = await c.post(
        "/api/v1/webhooks/telegram",
        json={"message": {"text": f"/start {code}", "chat": {"id": 4242}}},
    )
    assert wh.status_code == 200, wh.text
    status = await c.get("/api/v1/telegram/link", headers=h)
    assert status.json()["linked"] is True
    assert status.json()["chat_id"] == "4242"


@pytest.mark.asyncio
async def test_inbound_cross_tenant(env_i):
    c, settings = env_i
    a = await signup(c)
    b = await signup(c)
    ah = a.h(a.personal)
    addr = (await c.get("/api/v1/inbound/address", headers=ah)).json()
    token = addr["address"].split("alerts+")[1].split("@")[0]
    raw = (FIXTURES / "indeed.eml").read_bytes()
    sig = hmac.new(settings.inbound_webhook_secret.encode(), raw, hashlib.sha256).hexdigest()
    await c.post(
        f"/api/v1/webhooks/inbound-email?token={token}",
        content=raw,
        headers={"X-Kame-Signature": f"sha256={sig}"},
    )
    bh = b.h(b.personal)
    msgs = await c.get("/api/v1/inbound/messages", headers=bh)
    assert msgs.status_code == 200
    assert msgs.json() == []


@pytest.fixture
async def env_unsecreted():
    """A deployed-like environment that forgot to configure the webhook secrets."""
    settings = Settings(
        database_url=TEST_DB_URL,
        environment="dev",
        log_json=False,
        auth_rate_limit_enabled=False,
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c, settings


@pytest.mark.asyncio
async def test_webhooks_fail_closed_without_a_secret(env_unsecreted):
    c, _ = env_unsecreted
    tg = await c.post("/api/v1/webhooks/telegram", json={"message": {"text": "/start x"}})
    assert tg.status_code == 401
    mail = await c.post("/api/v1/webhooks/inbound-email?token=abc", content=b"raw")
    assert mail.status_code == 401


@pytest.mark.asyncio
async def test_telegram_webhook_rejects_a_wrong_secret(env_i):
    c, settings = env_i
    settings.telegram_webhook_secret = "s3cret"
    bad = await c.post(
        "/api/v1/webhooks/telegram",
        json={"message": {"text": "/start x"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "nope"},
    )
    assert bad.status_code == 401
    good = await c.post(
        "/api/v1/webhooks/telegram",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "s3cret"},
    )
    assert good.status_code == 200


def test_prod_requires_a_telegram_secret_when_the_bot_is_enabled():
    with pytest.raises(ValueError, match="TELEGRAM_WEBHOOK_SECRET"):
        Settings(
            environment="prod",
            jwt_secret="x" * 40,
            master_kek="MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
            cookie_secure=True,
            telegram_bot_token="123:abc",
        )
