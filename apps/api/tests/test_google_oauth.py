import re
import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth.google import GoogleOAuth, GoogleProfile, new_pkce
from app.core.config import Settings
from app.core.mail import Outbox
from app.main import create_app
from tests.conftest import TEST_DB_URL
from tests.test_workspaces import signup


class FakeGoogle(GoogleOAuth):
    def __init__(self, settings):
        super().__init__(settings)
        self.profile: GoogleProfile | None = None
        self.seen: dict = {}

    async def fetch_profile(self, *, code, verifier):
        self.seen = {"code": code, "verifier": verifier}
        if code == "bad":
            raise RuntimeError("token exchange failed")
        assert self.profile
        return self.profile


@pytest.fixture
async def env():
    s = Settings(
        database_url=TEST_DB_URL,
        environment="test",
        log_json=False,
        auth_rate_limit_enabled=False,
        google_client_id="cid",
        google_client_secret="secret",
    )
    app = create_app(s)
    app.state.mailer = Outbox()
    app.state.google = FakeGoogle(s)
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            yield c, app.state.google


def new_profile(email=None, verified=True):
    return GoogleProfile(
        uuid.uuid4().hex, email or f"g-{uuid.uuid4().hex[:8]}@example.com", verified, "Gina"
    )


async def start(c):
    r = await c.get("/api/v1/auth/google/start")
    assert r.status_code == 302
    q = parse_qs(urlparse(r.headers["location"]).query)
    return q


async def callback(c, g, profile, code="ok"):
    g.profile = profile
    q = await start(c)
    return await c.get(
        "/api/v1/auth/google/callback", params={"code": code, "state": q["state"][0]}
    )


def test_pkce_challenge_matches_verifier():
    import base64
    import hashlib

    v, ch = new_pkce()
    assert base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b"=").decode() == ch


async def test_start_redirects_to_google_with_pkce_and_state(env):
    c, _ = env
    q = await start(c)
    assert q["client_id"] == ["cid"] and q["code_challenge_method"] == ["S256"]
    assert q["redirect_uri"] == ["http://localhost:8100/api/v1/auth/google/callback"]
    assert "kame_oauth" in c.cookies


async def test_not_configured_is_404():
    app = create_app(Settings(database_url=TEST_DB_URL, environment="test", log_json=False))
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            assert (await c.get("/api/v1/auth/google/start")).status_code == 404
            assert (await c.get("/api/v1/auth/providers")).json() == {"google": False}


async def test_new_google_user_gets_session_verified_email_and_personal_workspace(env):
    c, g = env
    p = new_profile()
    r = await callback(c, g, p)
    assert r.status_code == 302 and r.headers["location"] == "http://localhost:3100/auth/callback"
    assert g.seen["verifier"]
    tok = (await c.post("/api/v1/auth/refresh")).json()
    h = {"Authorization": f"Bearer {tok['access_token']}"}
    assert tok["user"]["email"] == p.email and tok["user"]["email_verified"] is True
    wss = (await c.get("/api/v1/workspaces", headers=h)).json()
    assert [(w["kind"], w["role"]) for w in wss] == [("personal", "owner")]


async def test_returning_google_user_logs_in_to_the_same_account(env):
    c, g = env
    p = new_profile()
    await callback(c, g, p)
    first = (await c.post("/api/v1/auth/refresh")).json()["user"]["id"]
    c.cookies.clear()
    r = await callback(c, g, p)
    assert r.headers["location"].endswith("/auth/callback")
    assert (await c.post("/api/v1/auth/refresh")).json()["user"]["id"] == first


async def test_google_email_matching_a_password_account_is_not_merged(env):
    c, g = env
    existing = await signup(c)
    c.cookies.clear()
    r = await callback(c, g, new_profile(email=existing.email))
    assert r.headers["location"] == "http://localhost:3100/login?error=account_exists"
    assert "kame_refresh" not in c.cookies


async def test_unverified_google_email_is_refused(env):
    c, g = env
    r = await callback(c, g, new_profile(verified=False))
    assert r.headers["location"].endswith("error=email_not_verified")


async def test_signed_in_user_can_link_google_then_use_it(env):
    c, g = env
    me = await signup(c)
    p = new_profile(email=f"other-{uuid.uuid4().hex[:6]}@example.com")  # email may differ
    g.profile = p
    r = await c.post("/api/v1/auth/google/link", headers=me.h())
    q = parse_qs(urlparse(r.json()["url"]).query)
    cb = await c.get("/api/v1/auth/google/callback", params={"code": "ok", "state": q["state"][0]})
    assert cb.headers["location"].endswith("/settings/profile?linked=google")
    c.cookies.clear()
    cb = await callback(c, g, p)
    tok = (await c.post("/api/v1/auth/refresh")).json()
    assert tok["user"]["email"] == me.email  # logged into the linked account, not a new one


async def test_google_identity_cannot_be_linked_to_two_accounts(env):
    c, g = env
    a, b = await signup(c), await signup(c)
    g.profile = new_profile()
    for who, expect in ((a, "linked=google"), (b, "error=identity_in_use")):
        r = await c.post("/api/v1/auth/google/link", headers=who.h())
        q = parse_qs(urlparse(r.json()["url"]).query)
        cb = await c.get(
            "/api/v1/auth/google/callback", params={"code": "ok", "state": q["state"][0]}
        )
        assert expect in cb.headers["location"]


async def test_state_mismatch_missing_cookie_and_failed_exchange_are_rejected(env):
    c, g = env
    g.profile = new_profile()
    await start(c)
    bad_state = await c.get(
        "/api/v1/auth/google/callback", params={"code": "ok", "state": "forged"}
    )
    assert bad_state.headers["location"].endswith("error=oauth_failed")
    q = await start(c)
    failed = await c.get(
        "/api/v1/auth/google/callback", params={"code": "bad", "state": q["state"][0]}
    )
    assert failed.headers["location"].endswith("error=oauth_failed")
    c.cookies.clear()
    nocookie = await c.get("/api/v1/auth/google/callback", params={"code": "ok", "state": "x"})
    assert nocookie.headers["location"].endswith("error=oauth_cancelled")
    denied = await c.get("/api/v1/auth/google/callback", params={"error": "access_denied"})
    assert denied.headers["location"].endswith("error=oauth_cancelled")
    assert re.search(r"kame_refresh", str(c.cookies)) is None
