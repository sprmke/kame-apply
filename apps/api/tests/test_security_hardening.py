"""Regression tests for the Phase 2 security review (one test per finding)."""

import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.ai.providers import build_model, revalidate_base_url, validate_base_url
from app.auth.google import GoogleProfile
from app.core.config import Settings
from app.core.errors import AppError
from app.core.mail import Outbox
from app.main import create_app
from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_google_oauth import FakeGoogle
from tests.test_workspaces import PW, last_token, signup, verify_in_db


async def make_client(*, rate_limits=False, ip=("127.0.0.1", 5000)):
    s = Settings(
        database_url=TEST_DB_URL,
        environment="test",
        log_json=False,
        auth_rate_limit_enabled=rate_limits,
        google_client_id="cid",
        google_client_secret="secret",
    )
    app = create_app(s)
    app.state.mailer = Outbox()
    app.state.google = FakeGoogle(s)
    return app


@pytest.fixture
async def app_and_client():
    app = await make_client()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            yield app, c


# H1 ---------------------------------------------------------------------------------------------


async def test_unverified_account_cannot_link_google(app_and_client):
    _, c = app_and_client
    squatter = await signup(c, verified=False)
    r = await c.post("/api/v1/auth/google/link", headers=squatter.h())
    assert r.status_code == 409 and r.json()["error"]["code"] == "email_unverified"


async def test_link_then_unverified_state_cannot_sign_in_with_google(app_and_client):
    app, c = app_and_client
    me = await signup(c)  # verified
    app.state.google.profile = GoogleProfile(uuid.uuid4().hex, "someone@example.com", True, "G")
    url = (await c.post("/api/v1/auth/google/link", headers=me.h())).json()["url"]
    state = parse_qs(urlparse(url).query)["state"][0]
    cb = await c.get("/api/v1/auth/google/callback", params={"code": "ok", "state": state})
    assert "linked=google" in cb.headers["location"]
    # The mailbox is later reset to unverified (e.g. support action): the identity alone must not log in.
    e = create_async_engine(TEST_OWNER_URL)
    async with e.begin() as conn:
        await conn.execute(
            text("UPDATE users SET email_verified_at = NULL WHERE email = :e"), {"e": me.email}
        )
    await e.dispose()
    c.cookies.clear()
    q = parse_qs(urlparse((await c.get("/api/v1/auth/google/start")).headers["location"]).query)
    cb = await c.get("/api/v1/auth/google/callback", params={"code": "ok", "state": q["state"][0]})
    assert cb.headers["location"].endswith("error=email_unverified")


async def test_unlink_google_needs_a_password_and_audits(app_and_client):
    app, c = app_and_client
    me = await signup(c)
    app.state.google.profile = GoogleProfile(uuid.uuid4().hex, "x@example.com", True, "G")
    url = (await c.post("/api/v1/auth/google/link", headers=me.h())).json()["url"]
    await c.get(
        "/api/v1/auth/google/callback",
        params={"code": "ok", "state": parse_qs(urlparse(url).query)["state"][0]},
    )
    assert (await c.get("/api/v1/me", headers=me.h())).json()["providers"] == ["google"]
    assert (await c.delete("/api/v1/auth/google/link", headers=me.h())).status_code == 200
    assert (await c.get("/api/v1/me", headers=me.h())).json()["providers"] == []
    # A Google-only account cannot remove its only way in.
    c.cookies.clear()
    app.state.google.profile = GoogleProfile(
        uuid.uuid4().hex, f"only-{uuid.uuid4().hex[:6]}@example.com", True, "Only"
    )
    q = parse_qs(urlparse((await c.get("/api/v1/auth/google/start")).headers["location"]).query)
    await c.get("/api/v1/auth/google/callback", params={"code": "ok", "state": q["state"][0]})
    tok = (await c.post("/api/v1/auth/refresh")).json()["access_token"]
    r = await c.delete("/api/v1/auth/google/link", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "last_sign_in_method"


# M3 / L3 ----------------------------------------------------------------------------------------


async def test_session_has_an_absolute_lifetime(app_and_client):
    _, c = app_and_client
    await signup(c)
    e = create_async_engine(TEST_OWNER_URL)
    async with e.begin() as conn:
        await conn.execute(
            text(
                "UPDATE user_sessions SET created_at = now() - interval '91 days' WHERE revoked_at IS NULL"
            )
        )
    await e.dispose()
    assert (await c.post("/api/v1/auth/refresh")).status_code == 401


# M4 / M5 ----------------------------------------------------------------------------------------


async def test_unverified_accounts_can_neither_invite_nor_accept(app_and_client):
    app, c = app_and_client
    owner = await signup(c)
    ws = (await c.post("/api/v1/workspaces", json={"name": "Crew"}, headers=owner.h())).json()["id"]
    guest = await signup(c, verified=False)
    await c.post("/api/v1/workspace/invitations", json={"email": guest.email}, headers=owner.h(ws))
    token = last_token(app.state.mailer)
    r = await c.post("/api/v1/invitations/accept", json={"token": token}, headers=guest.h())
    assert r.status_code == 409 and r.json()["error"]["code"] == "email_unverified"
    await verify_in_db(guest.email)
    assert (
        await c.post("/api/v1/invitations/accept", json={"token": token}, headers=guest.h())
    ).status_code == 200

    spammer = await signup(c, verified=False)
    sws = (
        await c.post("/api/v1/workspaces", json={"name": "Free money"}, headers=spammer.h())
    ).json()["id"]
    r = await c.post(
        "/api/v1/workspace/invitations",
        json={"email": "victim@example.com"},
        headers=spammer.h(sws),
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "email_unverified"


async def test_invitations_are_rate_limited():
    app = await make_client(rate_limits=True)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            owner = await signup(c)
            ws = (
                await c.post("/api/v1/workspaces", json={"name": "Spam"}, headers=owner.h())
            ).json()["id"]
            e = create_async_engine(TEST_OWNER_URL)
            async with e.begin() as conn:
                await conn.execute(
                    text(
                        "INSERT INTO workspace_limits (workspace_id, max_members) VALUES (:w, 500)"
                    ),
                    {"w": uuid.UUID(ws)},
                )
            await e.dispose()
            codes = [
                (
                    await c.post(
                        "/api/v1/workspace/invitations",
                        json={"email": f"t{i}@example.com"},
                        headers=owner.h(ws),
                    )
                ).status_code
                for i in range(22)
            ]
    assert codes[:20] == [201] * 20 and codes[20:] == [429, 429]


# M8 ---------------------------------------------------------------------------------------------


async def test_a_stranger_cannot_lock_a_victim_out_of_login():
    app = await make_client(rate_limits=True)
    async with app.router.lifespan_context(app):
        victim_ip, attacker_ip = ("10.0.0.1", 1), ("10.0.0.2", 2)
        async with AsyncClient(
            transport=ASGITransport(app=app, client=victim_ip), base_url="http://t"
        ) as victim:
            email = f"v-{uuid.uuid4().hex[:8]}@example.com"
            await victim.post("/api/v1/auth/register", json={"email": email, "password": PW})
        async with AsyncClient(
            transport=ASGITransport(app=app, client=attacker_ip), base_url="http://t"
        ) as attacker:
            codes = [
                (
                    await attacker.post(
                        "/api/v1/auth/login", json={"email": email, "password": "wrong-password-1"}
                    )
                ).status_code
                for _ in range(7)
            ]
            assert 429 in codes  # the attacker is throttled
        async with AsyncClient(
            transport=ASGITransport(app=app, client=victim_ip), base_url="http://t"
        ) as victim:
            ok = await victim.post("/api/v1/auth/login", json={"email": email, "password": PW})
            assert ok.status_code == 200  # the real owner is not locked out


# M2 ---------------------------------------------------------------------------------------------


def test_unset_environment_is_production_and_refuses_dev_secrets(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    s_kwargs = {"_env_file": None}
    with pytest.raises(ValueError):
        Settings(**s_kwargs)  # type: ignore[arg-type]


# M1 ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://100.64.0.1:11434",  # CGNAT is not global
        "http://[::ffff:127.0.0.1]:11434",  # IPv4-mapped loopback
        "http://example.com:22/",  # port outside the allowlist
        "http://169.254.169.254/",
        "http://10.0.0.5/",
    ],
)
def test_hosted_ollama_url_rejects_internal_targets(url):
    with pytest.raises(AppError):
        validate_base_url(url, allow_private=False)


async def test_call_time_revalidation_blocks_a_url_that_turned_private():
    with pytest.raises(AppError):
        await revalidate_base_url("http://127.0.0.1:11434/v1", allow_private=False)
    await revalidate_base_url("http://127.0.0.1:11434/v1", allow_private=True)


def test_ollama_client_does_not_follow_redirects():
    model = build_model(
        "ollama", api_key=None, model="llama3.2", base_url="http://localhost:11434/v1"
    )
    client = model._provider.client  # pyright: ignore[reportAttributeAccessIssue]
    assert client._client.follow_redirects is False


# L1 ---------------------------------------------------------------------------------------------


async def test_short_api_keys_are_rejected(app_and_client):
    _, c = app_and_client
    me = await signup(c)
    r = await c.post(
        "/api/v1/ai/credentials",
        json={"provider": "gemini", "api_key": "abc"},
        headers=me.h(me.personal),
    )
    assert r.status_code == 422


# M10 --------------------------------------------------------------------------------------------


async def test_read_only_role_cannot_read_tenant_or_credential_tables():
    e = create_async_engine(TEST_OWNER_URL)
    async with e.connect() as conn:
        tables = (
            "activity_log",
            "workspaces",
            "workspace_members",
            "invitations",
            "ai_credentials",
            "workspace_keys",
            "ai_usage",
            "user_sessions",
            "refresh_tokens",
            "auth_tokens",
            "oauth_identities",
            "workspace_limits",
        )
        leaks = [
            t
            for t in tables
            if (
                await conn.execute(
                    text("SELECT has_table_privilege('kame_apply_ro', :t, 'SELECT')"), {"t": t}
                )
            ).scalar_one()
        ]
        pw = (
            await conn.execute(
                text(
                    "SELECT has_column_privilege('kame_apply_ro', 'users', 'password_hash', 'SELECT')"
                )
            )
        ).scalar_one()
    await e.dispose()
    assert leaks == [] and pw is False
