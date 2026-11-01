import uuid

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.messages import ModelResponse, TextPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.ai import crypto, service
from app.ai.providers import cost_micros, validate_base_url
from app.core.config import Settings
from app.core.errors import AppError
from app.core.mail import Outbox
from app.core.security import WorkspaceContext, require_action
from app.main import create_app
from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_workspaces import Who, signup, team_with

SECRET = "sk-test-SUPERSECRETVALUE1234"
calls: list[dict] = []
behavior = {"mode": "ok"}


def fake_factory(provider, *, api_key, model, base_url):
    """Stands in for build_model: records what the router asked for, never touches the network."""

    def respond(messages, info):
        calls.append({"provider": provider, "api_key": api_key, "model": model})
        if behavior["mode"] == "401":
            raise ModelHTTPError(401, model, {"error": "bad key"})
        if behavior["mode"] == "gemini400":
            raise ModelHTTPError(
                400,
                model,
                {
                    "error": {
                        "status": "INVALID_ARGUMENT",
                        "details": [{"reason": "API_KEY_INVALID"}],
                    }
                },
            )
        if behavior["mode"] == "500":
            raise ModelHTTPError(500, model, {"error": "boom"})
        return ModelResponse(
            parts=[TextPart("ok")], usage=RequestUsage(input_tokens=1000, output_tokens=500)
        )

    return FunctionModel(respond)


@pytest.fixture(autouse=True)
def _reset():
    calls.clear()
    behavior["mode"] = "ok"


@pytest.fixture
async def env():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    app.state.mailer = Outbox()
    app.state.model_factory = fake_factory

    @app.post("/api/v1/_ai_probe")
    async def probe(
        tier: str = "standard", ctx: WorkspaceContext = Depends(require_action("data.write"))
    ):
        r = await service.run_text(
            ctx,
            app.state.settings,
            tier=tier,
            feature="probe",
            system="s",
            prompt="p",
            model_factory=app.state.model_factory,
        )
        return {"text": r.text, "provider": r.provider, "model": r.model, "cost": r.cost_micros}

    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c, app.state.mailer


async def team(c, outbox):
    owner = await signup(c)
    ws, p = await team_with(c, owner, outbox, {"ad": "admin", "m": "member", "v": "viewer"})
    return owner, ws, p


async def add(c, who: Who, ws, provider="gemini", key=SECRET, **kw):
    r = await c.post(
        "/api/v1/ai/credentials",
        json={"provider": provider, "api_key": key, **kw},
        headers=who.h(ws),
    )
    assert r.status_code == 201, r.text
    return r.json()


# --- crypto -----------------------------------------------------------------------------------


def test_envelope_roundtrip_and_aad_binding():
    kek = crypto.parse_kek("ZGV2LW9ubHktbWFzdGVyLWtleS0wMTIzNDU2Nzg5YWI=")
    ws1, ws2 = uuid.uuid4(), uuid.uuid4()
    dek = crypto.unwrap_dek(kek, crypto.new_wrapped_dek(kek, ws1), ws1)
    blob = crypto.encrypt_secret(dek, SECRET, ws1)
    assert SECRET.encode() not in blob
    assert crypto.decrypt_secret(dek, blob, ws1) == SECRET
    with pytest.raises(AppError):  # ciphertext moved to another workspace
        crypto.decrypt_secret(dek, blob, ws2)
    with pytest.raises(AppError):  # tampering
        crypto.decrypt_secret(dek, blob[:-1] + bytes([blob[-1] ^ 1]), ws1)
    with pytest.raises(AppError):  # wrong workspace for the wrapped DEK
        crypto.unwrap_dek(kek, crypto.new_wrapped_dek(kek, ws1), ws2)


def test_prod_rejects_the_public_dev_master_key():
    with pytest.raises(ValueError):
        Settings(environment="prod", jwt_secret="x" * 40, cookie_secure=True)


def test_cost_estimate_uses_model_prices():
    assert cost_micros("gemini", "gemini-3.5-flash", 1_000_000, 0) == 300_000
    assert cost_micros("ollama", "llama3.2", 10**6, 10**6) == 0


def test_base_url_blocks_private_hosts_when_hosted():
    for bad in (
        "http://127.0.0.1:11434",
        "http://localhost/v1",
        "http://169.254.169.254/",
        "ftp://x.com",
    ):
        with pytest.raises(AppError):
            validate_base_url(bad, allow_private=False)
    assert (
        validate_base_url("http://127.0.0.1:11434/", allow_private=True) == "http://127.0.0.1:11434"
    )


# --- credentials -------------------------------------------------------------------------------


async def test_key_is_encrypted_at_rest_and_never_returned(env):
    c, outbox = env
    owner, ws, _ = await team(c, outbox)
    created = await add(c, owner, ws, label="main")
    listed = (await c.get("/api/v1/ai/credentials", headers=owner.h(ws))).json()
    assert SECRET not in str(created) + str(listed)
    assert listed[0]["key_hint"] == SECRET[-4:] and listed[0]["status"] == "untested"
    e = create_async_engine(TEST_OWNER_URL)
    async with e.connect() as conn:
        blob = (
            await conn.execute(
                text("SELECT encrypted_key FROM ai_credentials WHERE id=:i"),
                {"i": uuid.UUID(created["id"])},
            )
        ).scalar_one()
        wrapped = (
            await conn.execute(
                text("SELECT wrapped_dek FROM workspace_keys WHERE workspace_id=:w"),
                {"w": uuid.UUID(ws)},
            )
        ).scalar_one()
        audit = (
            (
                await conn.execute(
                    text(
                        "SELECT after::text FROM activity_log WHERE action='ai_credential.added' AND workspace_id=:w"
                    ),
                    {"w": uuid.UUID(ws)},
                )
            )
            .scalars()
            .all()
        )
    await e.dispose()
    assert SECRET.encode() not in bytes(blob) and len(bytes(wrapped)) > 32
    assert all(SECRET not in a for a in audit)


async def test_credential_rbac(env):
    c, outbox = env
    _, ws, p = await team(c, outbox)
    body = {"provider": "gemini", "api_key": SECRET}
    for who in (p["m"], p["v"]):
        assert (
            await c.post("/api/v1/ai/credentials", json=body, headers=who.h(ws))
        ).status_code == 403
        assert (await c.get("/api/v1/ai/credentials", headers=who.h(ws))).status_code == 403
    assert (
        await c.post("/api/v1/ai/credentials", json=body, headers=p["ad"].h(ws))
    ).status_code == 201
    # Usage is readable by everyone, including viewers.
    assert (await c.get("/api/v1/ai/usage", headers=p["v"].h(ws))).status_code == 200


async def test_credential_validation(env):
    c, outbox = env
    owner, ws, _ = await team(c, outbox)
    post = lambda body: c.post("/api/v1/ai/credentials", json=body, headers=owner.h(ws))  # noqa: E731
    assert (await post({"provider": "nope", "api_key": "x-12345678"})).json()["error"][
        "code"
    ] == "unknown_provider"
    assert (await post({"provider": "gemini"})).json()["error"]["code"] == "key_required"
    assert (
        await post({"provider": "gemini", "api_key": "k-12345678", "base_url": "http://x.com"})
    ).json()["error"]["code"] == "invalid_base_url"
    assert (
        await post({"provider": "ollama", "base_url": "http://localhost:11434/v1"})
    ).status_code == 201


async def test_credentials_are_tenant_isolated(env):
    c, outbox = env
    owner, ws, _ = await team(c, outbox)
    cred = await add(c, owner, ws)
    other = await signup(c)
    assert (await c.get("/api/v1/ai/credentials", headers=other.h(ws))).status_code == 404
    assert (await c.get("/api/v1/ai/credentials", headers=other.h(other.personal))).json() == []
    assert (
        await c.delete(f"/api/v1/ai/credentials/{cred['id']}", headers=other.h(other.personal))
    ).status_code == 404
    e = create_async_engine(TEST_DB_URL)
    async with e.begin() as conn:
        await conn.execute(
            text("SELECT set_config('app.workspace_id', :w, true)"), {"w": other.personal}
        )
        n = (
            await conn.execute(
                text(
                    "SELECT (SELECT count(*) FROM ai_credentials) + (SELECT count(*) FROM workspace_keys) + (SELECT count(*) FROM ai_usage)"
                )
            )
        ).scalar_one()
    await e.dispose()
    assert n == 0


async def test_test_endpoint_marks_valid_then_invalid(env):
    c, outbox = env
    owner, ws, _ = await team(c, outbox)
    cred = await add(c, owner, ws)
    r = await c.post(f"/api/v1/ai/credentials/{cred['id']}/test", headers=owner.h(ws))
    assert r.json() == {"status": "valid", "detail": None}
    assert calls[-1]["api_key"] == SECRET and calls[-1]["model"] == "gemini-3.5-flash-lite"
    behavior["mode"] = "401"
    r = await c.post(f"/api/v1/ai/credentials/{cred['id']}/test", headers=owner.h(ws))
    assert r.json()["status"] == "invalid"
    assert (await c.get("/api/v1/ai/credentials", headers=owner.h(ws))).json()[0][
        "status"
    ] == "invalid"
    behavior["mode"] = "500"  # provider outage must not flip the key's status
    cred2 = await add(c, owner, ws)
    r = await c.post(f"/api/v1/ai/credentials/{cred2['id']}/test", headers=owner.h(ws))
    assert r.json()["status"] == "error"


async def test_delete_credential(env):
    c, outbox = env
    owner, ws, _ = await team(c, outbox)
    cred = await add(c, owner, ws)
    assert (
        await c.delete(f"/api/v1/ai/credentials/{cred['id']}", headers=owner.h(ws))
    ).status_code == 200
    assert (await c.get("/api/v1/ai/credentials", headers=owner.h(ws))).json() == []


# --- running models ----------------------------------------------------------------------------


async def test_no_credential_means_a_clear_setup_error(env):
    c, outbox = env
    owner, ws, _ = await team(c, outbox)
    r = await c.post("/api/v1/_ai_probe", headers=owner.h(ws))
    assert r.status_code == 409 and r.json()["error"]["code"] == "ai_not_configured"


async def test_run_meters_usage_and_uses_tier_defaults(env):
    c, outbox = env
    owner, ws, _ = await team(c, outbox)
    await add(c, owner, ws)
    for tier, model in (
        ("bulk", "gemini-3.5-flash-lite"),
        ("standard", "gemini-3.5-flash"),
        ("premium", "gemini-3.1-pro-preview"),
    ):
        r = await c.post(f"/api/v1/_ai_probe?tier={tier}", headers=owner.h(ws))
        assert r.status_code == 200 and r.json()["model"] == model
    usage = (await c.get("/api/v1/ai/usage", headers=owner.h(ws))).json()
    assert usage["by_feature"][0]["feature"] == "probe" and usage["by_feature"][0]["calls"] == 3
    # 1000 in / 500 out on flash: 1000*0.3 + 500*2.5 = 1550 micros
    flash = (await c.post("/api/v1/_ai_probe?tier=standard", headers=owner.h(ws))).json()
    assert flash["cost"] == 1550
    assert usage["spent_micros"] > 0


async def test_tier_mapping_overrides_the_default(env):
    c, outbox = env
    owner, ws, _ = await team(c, outbox)
    await add(c, owner, ws, provider="gemini")
    await add(c, owner, ws, provider="groq", key="gsk-test-1234")
    bad = await c.patch(
        "/api/v1/ai/settings",
        json={"tier_models": {"bulk": {"provider": "nope", "model": "m"}}},
        headers=owner.h(ws),
    )
    assert bad.status_code == 422
    ok = await c.patch(
        "/api/v1/ai/settings",
        json={"tier_models": {"bulk": {"provider": "groq", "model": "openai/gpt-oss-20b"}}},
        headers=owner.h(ws),
    )
    assert ok.status_code == 200
    r = await c.post("/api/v1/_ai_probe?tier=bulk", headers=owner.h(ws))
    assert r.json()["provider"] == "groq" and r.json()["model"] == "openai/gpt-oss-20b"
    assert (await c.post("/api/v1/_ai_probe?tier=standard", headers=owner.h(ws))).json()[
        "provider"
    ] == "gemini"


async def test_budget_guard_blocks_before_calling_the_model(env):
    c, outbox = env
    owner, ws, _ = await team(c, outbox)
    await add(c, owner, ws)
    await c.patch("/api/v1/ai/settings", json={"monthly_budget_cents": 0}, headers=owner.h(ws))
    r = await c.post("/api/v1/_ai_probe", headers=owner.h(ws))
    assert r.status_code == 402 and r.json()["error"]["code"] == "budget_reached"
    assert calls == []  # hard stop happened before any provider call
    await c.patch("/api/v1/ai/settings", json={"monthly_budget_cents": 500}, headers=owner.h(ws))
    assert (await c.post("/api/v1/_ai_probe", headers=owner.h(ws))).status_code == 200


async def test_budget_counts_spend_so_far(env):
    c, outbox = env
    owner, ws, _ = await team(c, outbox)
    await add(c, owner, ws)
    e = create_async_engine(TEST_OWNER_URL)
    async with e.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO ai_usage (workspace_id, provider, model, tier, feature, cost_micros) VALUES (:w,'gemini','m','bulk','seed', 4999000)"
            ),
            {"w": uuid.UUID(ws)},
        )
    await e.dispose()
    r = await c.post("/api/v1/_ai_probe", headers=owner.h(ws))
    assert r.status_code == 402 and r.json()["error"]["details"]["spent_cents"] == 499


async def test_usage_ledger_is_append_only_for_the_app_role(env):
    c, outbox = env
    owner, ws, _ = await team(c, outbox)
    await add(c, owner, ws)
    await c.post("/api/v1/_ai_probe", headers=owner.h(ws))
    e = create_async_engine(TEST_DB_URL)
    from sqlalchemy.exc import DBAPIError

    for stmt in ("UPDATE ai_usage SET cost_micros = 0", "DELETE FROM ai_usage"):
        with pytest.raises(DBAPIError):
            async with e.begin() as conn:
                await conn.execute(
                    text("SELECT set_config('app.workspace_id', :w, true)"), {"w": ws}
                )
                await conn.execute(text(stmt))
    await e.dispose()


async def test_rejected_key_surfaces_a_stable_error_code(env):
    c, outbox = env
    owner, ws, _ = await team(c, outbox)
    await add(c, owner, ws)
    behavior["mode"] = "401"
    r = await c.post("/api/v1/_ai_probe", headers=owner.h(ws))
    assert r.status_code == 409 and r.json()["error"]["code"] == "ai_credential_invalid"
    # The request transaction rolls back on errors, so only the test endpoint (which returns
    # normally) persists the `invalid` flag. Workflows own their transactions and commit it.


async def test_fallback_only_when_enabled(env):
    c, outbox = env
    owner, ws, _ = await team(c, outbox)
    g = await add(c, owner, ws, provider="gemini")
    await add(c, owner, ws, provider="groq", key="gsk-test-1234")
    for cid in (g["id"],):
        await c.post(f"/api/v1/ai/credentials/{cid}/test", headers=owner.h(ws))
    # make groq 'valid' so it is eligible as a fallback
    groq_id = next(
        x["id"]
        for x in (await c.get("/api/v1/ai/credentials", headers=owner.h(ws))).json()
        if x["provider"] == "groq"
    )
    await c.post(f"/api/v1/ai/credentials/{groq_id}/test", headers=owner.h(ws))
    calls.clear()

    def only_groq_ok(provider, *, api_key, model, base_url):
        def respond(messages, info):
            calls.append({"provider": provider})
            if provider == "gemini":
                raise ModelHTTPError(401, model, {})
            return ModelResponse(
                parts=[TextPart("ok")], usage=RequestUsage(input_tokens=1, output_tokens=1)
            )

        return FunctionModel(respond)

    c._transport.app.state.model_factory = only_groq_ok  # type: ignore[attr-defined]
    r = await c.post("/api/v1/_ai_probe", headers=owner.h(ws))
    assert r.status_code == 409  # no fallback by default
    await c.patch("/api/v1/ai/settings", json={"fallback_enabled": True}, headers=owner.h(ws))
    r = await c.post("/api/v1/_ai_probe", headers=owner.h(ws))
    assert r.status_code == 200 and r.json()["provider"] == "groq"


async def test_provider_400_api_key_invalid_marks_the_key_invalid(env):
    c, outbox = env
    owner, ws, _ = await team(c, outbox)
    cred = await add(c, owner, ws)
    behavior["mode"] = "gemini400"
    r = await c.post(f"/api/v1/ai/credentials/{cred['id']}/test", headers=owner.h(ws))
    assert r.json()["status"] == "invalid"
