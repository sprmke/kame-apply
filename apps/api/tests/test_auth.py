import re
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.core.mail import Outbox
from app.main import create_app
from tests.conftest import TEST_DB_URL, TEST_OWNER_URL

PW = "correct horse battery"


@pytest.fixture
async def ctx():
    """(client, outbox, settings) with rate limits off. Cookies persist on the client."""
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    app.state.mailer = Outbox()
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c, app.state.mailer, settings


def _email(tag: str = "u") -> str:
    import uuid

    return f"{tag}-{uuid.uuid4().hex[:10]}@example.com"


def _token_from(outbox: Outbox, subject: str) -> str:
    mail = [m for m in outbox.sent if m.subject == subject][-1]
    found = re.search(r"token=([\w-]+)", mail.text)
    assert found
    return found.group(1)


async def _register(c, email=None, password=PW):
    email = email or _email()
    r = await c.post("/api/v1/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return email, r.json()


def _auth(body):
    return {"Authorization": f"Bearer {body['access_token']}"}


async def test_register_returns_token_cookie_and_sends_verification(ctx):
    c, outbox, _ = ctx
    email, body = await _register(c)
    assert body["user"]["email"] == email and body["user"]["email_verified"] is False
    assert "kame_refresh" in c.cookies
    set_cookie = (
        await c.post("/api/v1/auth/login", json={"email": email, "password": PW})
    ).headers["set-cookie"]
    assert (
        "HttpOnly" in set_cookie
        and "SameSite=lax" in set_cookie
        and "Path=/api/v1/auth" in set_cookie
    )
    assert [m.to for m in outbox.sent] == [email]
    me = await c.get("/api/v1/me", headers=_auth(body))
    assert me.status_code == 200 and me.json()["email"] == email


async def test_register_duplicate_email_conflicts_case_insensitively(ctx):
    c, _, _ = ctx
    email, _ = await _register(c)
    r = await c.post("/api/v1/auth/register", json={"email": email.upper(), "password": PW})
    assert r.status_code == 409 and r.json()["error"]["code"] == "email_taken"


async def test_password_policy(ctx):
    c, _, _ = ctx
    r = await c.post("/api/v1/auth/register", json={"email": _email(), "password": "short"})
    assert r.status_code == 422


async def test_password_is_stored_as_argon2id_and_never_returned(ctx):
    c, _, _ = ctx
    email, body = await _register(c)
    assert PW not in str(body)
    e = create_async_engine(TEST_OWNER_URL)
    async with e.connect() as conn:
        h = (
            await conn.execute(text("SELECT password_hash FROM users WHERE email=:e"), {"e": email})
        ).scalar_one()
    await e.dispose()
    assert h.startswith("$argon2id$")


async def test_login_wrong_password_and_unknown_email_look_identical(ctx):
    c, _, _ = ctx
    email, _ = await _register(c)
    bad = await c.post("/api/v1/auth/login", json={"email": email, "password": "wrong-password-1"})
    unknown = await c.post(
        "/api/v1/auth/login", json={"email": _email(), "password": "wrong-password-1"}
    )
    assert bad.status_code == unknown.status_code == 401
    assert bad.json()["error"] == unknown.json()["error"]


async def test_protected_routes_reject_missing_garbage_and_expired_tokens(ctx):
    c, _, settings = ctx
    assert (await c.get("/api/v1/me")).status_code == 401
    assert (await c.get("/api/v1/me", headers={"Authorization": "Bearer nope"})).status_code == 401
    import jwt

    _, body = await _register(c)
    claims = jwt.decode(body["access_token"], options={"verify_signature": False})
    claims["exp"] = datetime.now(UTC) - timedelta(seconds=5)
    expired = jwt.encode(claims, settings.jwt_secret, algorithm="HS256")
    assert (
        await c.get("/api/v1/me", headers={"Authorization": f"Bearer {expired}"})
    ).status_code == 401
    forged = jwt.encode(
        claims | {"exp": datetime.now(UTC) + timedelta(hours=1)},
        "other-secret-xxxxxxxxxxxxxxxxxxxxxxxx",
        algorithm="HS256",
    )
    assert (
        await c.get("/api/v1/me", headers={"Authorization": f"Bearer {forged}"})
    ).status_code == 401
    none_alg = jwt.encode(
        claims | {"exp": datetime.now(UTC) + timedelta(hours=1)},
        None,  # pyright: ignore[reportArgumentType]
        algorithm="none",
    )
    assert (
        await c.get("/api/v1/me", headers={"Authorization": f"Bearer {none_alg}"})
    ).status_code == 401


async def test_refresh_rotates_and_reuse_revokes_the_session(ctx):
    c, _, _ = ctx
    await _register(c)
    first = c.cookies["kame_refresh"]
    r = await c.post("/api/v1/auth/refresh")
    assert r.status_code == 200
    second = c.cookies["kame_refresh"]
    assert first != second
    new_headers = _auth(r.json())
    assert (await c.get("/api/v1/me", headers=new_headers)).status_code == 200

    # Immediate replay (multi-tab race): rejected, but the session survives.
    c.cookies.clear()
    c.cookies.set("kame_refresh", first, path="/api/v1/auth")
    race = await c.post("/api/v1/auth/refresh")
    assert race.status_code == 401
    assert "set-cookie" not in race.headers  # must not erase the winning tab's new cookie
    assert (await c.get("/api/v1/me", headers=new_headers)).status_code == 200

    # Replay after the grace window: theft. The whole session dies.
    e = create_async_engine(TEST_OWNER_URL)
    async with e.begin() as conn:
        await conn.execute(
            text(
                "UPDATE refresh_tokens SET used_at = now() - interval '1 minute' WHERE used_at IS NOT NULL"
            )
        )
    await e.dispose()
    c.cookies.clear()
    c.cookies.set("kame_refresh", first, path="/api/v1/auth")
    assert (await c.post("/api/v1/auth/refresh")).status_code == 401
    assert (await c.get("/api/v1/me", headers=new_headers)).status_code == 401
    c.cookies.clear()
    c.cookies.set("kame_refresh", second, path="/api/v1/auth")
    assert (await c.post("/api/v1/auth/refresh")).status_code == 401


async def test_refresh_without_cookie_is_401(ctx):
    c, _, _ = ctx
    assert (await c.post("/api/v1/auth/refresh")).status_code == 401


async def test_logout_kills_access_and_refresh(ctx):
    c, _, _ = ctx
    _, body = await _register(c)
    assert (await c.post("/api/v1/auth/logout", headers=_auth(body))).status_code == 200
    assert (await c.get("/api/v1/me", headers=_auth(body))).status_code == 401
    assert (await c.post("/api/v1/auth/refresh")).status_code == 401


async def test_sessions_list_and_revoke_only_own(ctx):
    c, _, _ = ctx
    email, one = await _register(c)
    two = (await c.post("/api/v1/auth/login", json={"email": email, "password": PW})).json()
    sessions = (await c.get("/api/v1/me/sessions", headers=_auth(two))).json()
    assert len(sessions) == 2 and sum(s["current"] for s in sessions) == 1
    other = next(s for s in sessions if not s["current"])
    assert (
        await c.delete(f"/api/v1/me/sessions/{other['id']}", headers=_auth(two))
    ).status_code == 200
    assert (await c.get("/api/v1/me", headers=_auth(one))).status_code == 401
    assert (await c.get("/api/v1/me", headers=_auth(two))).status_code == 200
    # Someone else's session id looks like a missing one.
    _, stranger = await _register(c)
    assert (
        await c.delete(f"/api/v1/me/sessions/{other['id']}", headers=_auth(stranger))
    ).status_code == 404


async def test_email_verification_is_single_use(ctx):
    c, outbox, _ = ctx
    _, body = await _register(c)
    token = _token_from(outbox, "Verify your email")
    assert (await c.post("/api/v1/auth/verify-email", json={"token": token})).status_code == 200
    assert (await c.get("/api/v1/me", headers=_auth(body))).json()["email_verified"] is True
    again = await c.post("/api/v1/auth/verify-email", json={"token": token})
    assert again.status_code == 400 and again.json()["error"]["code"] == "invalid_token"
    assert (await c.post("/api/v1/auth/verify-email", json={"token": "x" * 40})).status_code == 400


async def test_resend_verification_voids_the_old_link(ctx):
    c, outbox, _ = ctx
    _, body = await _register(c)
    old = _token_from(outbox, "Verify your email")
    assert (
        await c.post("/api/v1/auth/verify-email/resend", headers=_auth(body))
    ).status_code == 202
    new = _token_from(outbox, "Verify your email")
    assert old != new
    assert (await c.post("/api/v1/auth/verify-email", json={"token": old})).status_code == 400
    assert (await c.post("/api/v1/auth/verify-email", json={"token": new})).status_code == 200


async def test_password_reset_flow_ends_all_sessions(ctx):
    c, outbox, _ = ctx
    email, body = await _register(c)
    r = await c.post("/api/v1/auth/password/forgot", json={"email": email})
    assert r.status_code == 202
    token = _token_from(outbox, "Reset your password")
    new_pw = "a brand new passphrase"
    assert (
        await c.post("/api/v1/auth/password/reset", json={"token": token, "password": new_pw})
    ).status_code == 200
    assert (await c.get("/api/v1/me", headers=_auth(body))).status_code == 401
    assert (
        await c.post("/api/v1/auth/login", json={"email": email, "password": PW})
    ).status_code == 401
    ok = await c.post("/api/v1/auth/login", json={"email": email, "password": new_pw})
    assert ok.status_code == 200 and ok.json()["user"]["email_verified"] is True
    assert (
        await c.post("/api/v1/auth/password/reset", json={"token": token, "password": new_pw})
    ).status_code == 400


async def test_forgot_password_does_not_reveal_whether_the_account_exists(ctx):
    c, outbox, _ = ctx
    known, _ = await _register(c)
    before = len(outbox.sent)
    a = await c.post("/api/v1/auth/password/forgot", json={"email": known})
    b = await c.post("/api/v1/auth/password/forgot", json={"email": _email()})
    assert a.status_code == b.status_code == 202 and a.json() == b.json()
    assert len(outbox.sent) == before + 1


async def test_expired_reset_token_is_rejected(ctx):
    c, outbox, _ = ctx
    email, _ = await _register(c)
    await c.post("/api/v1/auth/password/forgot", json={"email": email})
    token = _token_from(outbox, "Reset your password")
    e = create_async_engine(TEST_OWNER_URL)
    async with e.begin() as conn:
        await conn.execute(
            text(
                "UPDATE auth_tokens SET expires_at = now() - interval '1 minute' WHERE kind='password_reset'"
            )
        )
    await e.dispose()
    assert (
        await c.post("/api/v1/auth/password/reset", json={"token": token, "password": PW})
    ).status_code == 400


async def test_tokens_are_stored_hashed(ctx):
    c, outbox, _ = ctx
    await _register(c)
    raw_refresh = c.cookies["kame_refresh"]
    raw_verify = _token_from(outbox, "Verify your email")
    e = create_async_engine(TEST_OWNER_URL)
    async with e.connect() as conn:
        rows = (
            (
                await conn.execute(
                    text(
                        "SELECT token_hash FROM refresh_tokens UNION ALL SELECT token_hash FROM auth_tokens"
                    )
                )
            )
            .scalars()
            .all()
        )
    await e.dispose()
    assert raw_refresh not in rows and raw_verify not in rows


async def test_update_me_validates_timezone_and_audits(ctx):
    c, _, _ = ctx
    _, body = await _register(c)
    bad = await c.patch("/api/v1/me", json={"timezone": "Mars/Olympus"}, headers=_auth(body))
    assert bad.status_code == 422
    ok = await c.patch(
        "/api/v1/me", json={"timezone": "Asia/Manila", "name": "Mika"}, headers=_auth(body)
    )
    assert ok.status_code == 200 and ok.json()["timezone"] == "Asia/Manila"
    e = create_async_engine(TEST_OWNER_URL)
    async with e.connect() as conn:
        n = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM activity_log WHERE action IN ('auth.registered','user.updated') AND workspace_id IS NULL"
                )
            )
        ).scalar_one()
    await e.dispose()
    assert n >= 2


async def test_login_is_rate_limited_per_email():
    settings = Settings(database_url=TEST_DB_URL, environment="test", log_json=False)
    app = create_app(settings)
    app.state.mailer = Outbox()
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            email = _email()
            codes = [
                (
                    await c.post(
                        "/api/v1/auth/login", json={"email": email, "password": "wrong-password-1"}
                    )
                ).status_code
                for _ in range(7)
            ]
    assert codes[:5] == [401] * 5 and codes[5:] == [429, 429]


def test_prod_refuses_default_secrets():
    with pytest.raises(ValueError):
        Settings(environment="prod")
