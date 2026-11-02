import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.ai import crypto
from tests.conftest import TEST_OWNER_URL
from tests.test_ai import add, env, team  # noqa: F401  (env fixture)
from tests.test_workspaces import signup, team_with


async def test_activity_requires_manager_filters_and_paginates(env):  # noqa: F811
    c, outbox = env
    owner, ws, p = await team(c, outbox)
    for who in (p["m"], p["v"]):
        assert (await c.get("/api/v1/activity", headers=who.h(ws))).status_code == 403
    await c.patch("/api/v1/workspace", json={"name": "One"}, headers=owner.h(ws))
    await c.patch("/api/v1/workspace", json={"name": "Two"}, headers=owner.h(ws))
    all_ = (await c.get("/api/v1/activity", headers=p["ad"].h(ws))).json()
    assert all_["items"][0]["action"] == "workspace.renamed"
    assert all_["items"][0]["after"] == {"name": "Two"}
    only = (await c.get("/api/v1/activity?action=workspace.renamed", headers=owner.h(ws))).json()
    assert [i["action"] for i in only["items"]] == ["workspace.renamed"] * 2
    prefix = (await c.get("/api/v1/activity?action=member.", headers=owner.h(ws))).json()
    assert {i["action"] for i in prefix["items"]} == {"member.joined"}
    page = (await c.get("/api/v1/activity?limit=2", headers=owner.h(ws))).json()
    assert len(page["items"]) == 2 and page["next_before"] and page["next_before_id"]
    nxt = (
        await c.get(
            "/api/v1/activity",
            params={
                "limit": 2,
                "before": page["next_before"],
                "before_id": page["next_before_id"],
            },
            headers=owner.h(ws),
        )
    ).json()
    assert {i["id"] for i in nxt["items"]}.isdisjoint({i["id"] for i in page["items"]})
    assert (await c.get("/api/v1/activity?limit=0", headers=owner.h(ws))).status_code == 422


async def test_activity_pagination_does_not_drop_rows_sharing_a_timestamp(env):  # noqa: F811
    """Rows written in one transaction share created_at; the id must break the tie."""
    c, outbox = env
    owner, ws, _p = await team(c, outbox)
    # Five rows, one transaction, one timestamp.
    e = create_async_engine(TEST_OWNER_URL)
    async with e.begin() as conn:
        for _ in range(5):
            await conn.execute(
                text(
                    "INSERT INTO activity_log (id, workspace_id, actor_type, action) "
                    "VALUES (gen_random_uuid(), :w, 'user', 'test.tied')"
                ),
                {"w": uuid.UUID(ws)},
            )
    await e.dispose()

    seen: list[str] = []
    cursor: dict[str, str] = {"limit": "2", "action": "test.tied"}
    for _ in range(4):
        page = (await c.get("/api/v1/activity", params=cursor, headers=owner.h(ws))).json()
        seen.extend(i["id"] for i in page["items"])
        if not page["next_before"]:
            break
        cursor = {
            "limit": "2",
            "action": "test.tied",
            "before": page["next_before"],
            "before_id": page["next_before_id"],
        }
    assert len(seen) == 5
    assert len(set(seen)) == 5


async def test_activity_never_crosses_workspaces_or_shows_platform_rows(env):  # noqa: F811
    c, _ = env
    a, b = await signup(c), await signup(c)
    items = (await c.get("/api/v1/activity", headers=a.h(a.personal))).json()["items"]
    assert items and all(i["action"].startswith(("workspace.", "member.")) for i in items)
    assert not any("auth." in i["action"] for i in items)  # platform events stay hidden
    assert (await c.get("/api/v1/activity", headers=b.h(a.personal))).status_code == 404


async def test_member_cap_counts_pending_invitations(env):  # noqa: F811
    c, outbox = env
    owner = await signup(c)
    ws, _ = await team_with(c, owner, outbox, {})
    e = create_async_engine(TEST_OWNER_URL)
    async with e.begin() as conn:
        await conn.execute(
            text("INSERT INTO workspace_limits (workspace_id, max_members) VALUES (:w, 2)"),
            {"w": uuid.UUID(ws)},
        )
    await e.dispose()

    def inv(email):
        return c.post("/api/v1/workspace/invitations", json={"email": email}, headers=owner.h(ws))

    assert (await inv("a1@example.com")).status_code == 201
    r = await inv("a2@example.com")
    assert r.status_code == 409 and r.json()["error"]["code"] == "member_limit"
    lim = (await c.get("/api/v1/workspace/limits", headers=owner.h(ws))).json()
    assert lim["max_members"] == 2 and lim["members_used"] == 2


async def test_app_role_cannot_raise_its_own_limits(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    e = create_async_engine(os.environ["DATABASE_URL"])
    from sqlalchemy.exc import DBAPIError

    with pytest.raises(DBAPIError):
        async with e.begin() as conn:
            await conn.execute(
                text("SELECT set_config('app.workspace_id', :w, true)"), {"w": me.personal}
            )
            await conn.execute(
                text("INSERT INTO workspace_limits (workspace_id, max_members) VALUES (:w, 999)"),
                {"w": uuid.UUID(me.personal)},
            )
    await e.dispose()


async def test_credential_cap_and_budget_cap_follow_limits(env):  # noqa: F811
    c, outbox = env
    owner, ws, _ = await team(c, outbox)
    e = create_async_engine(TEST_OWNER_URL)
    async with e.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO workspace_limits (workspace_id, max_ai_credentials, max_ai_budget_cents) VALUES (:w, 1, 1000)"
            ),
            {"w": uuid.UUID(ws)},
        )
    await e.dispose()
    await add(c, owner, ws)
    r = await c.post(
        "/api/v1/ai/credentials",
        json={"provider": "gemini", "api_key": "k-123456"},
        headers=owner.h(ws),
    )
    assert r.status_code == 409 and r.json()["error"]["code"] == "credential_limit"
    big = await c.patch(
        "/api/v1/ai/settings", json={"monthly_budget_cents": 1001}, headers=owner.h(ws)
    )
    assert big.status_code == 422 and big.json()["error"]["code"] == "budget_above_limit"


async def test_kek_rewrap_script(env):  # noqa: F811
    import base64

    from app.ops.rewrap_keks import rewrap

    c, outbox = env
    owner, ws, _ = await team(c, outbox)
    cred = await add(c, owner, ws)
    old = "ZGV2LW9ubHktbWFzdGVyLWtleS0wMTIzNDU2Nzg5YWI="
    new = base64.b64encode(os.urandom(32)).decode()
    done, _skipped = await rewrap(new, old, TEST_OWNER_URL)
    assert done >= 1
    again, skipped = await rewrap(new, old, TEST_OWNER_URL)
    assert again == 0 and skipped >= 1  # idempotent
    e = create_async_engine(TEST_OWNER_URL)
    async with e.connect() as conn:
        wrapped, blob = (
            await conn.execute(
                text(
                    "SELECT k.wrapped_dek, c.encrypted_key FROM workspace_keys k JOIN ai_credentials c ON c.workspace_id=k.workspace_id WHERE c.id=:i"
                ),
                {"i": uuid.UUID(cred["id"])},
            )
        ).one()
    dek = crypto.unwrap_dek(crypto.parse_kek(new), bytes(wrapped), uuid.UUID(ws))
    assert crypto.decrypt_secret(dek, bytes(blob), uuid.UUID(ws)) == "sk-test-SUPERSECRETVALUE1234"
    # restore the dev key so later tests in this session still decrypt
    await rewrap(old, new, TEST_OWNER_URL)
    await e.dispose()


async def test_logout_writes_a_session_revoked_audit_event(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    out = await c.post("/api/v1/auth/logout", headers=h)
    assert out.status_code in {200, 204}
    e = create_async_engine(TEST_OWNER_URL)
    async with e.begin() as conn:
        n = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM activity_log "
                    "WHERE action = 'auth.session_revoked' AND actor_id = :u"
                ),
                {"u": me.id},
            )
        ).scalar_one()
    await e.dispose()
    assert n == 1
