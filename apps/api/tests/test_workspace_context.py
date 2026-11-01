import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.rbac import ACTIONS, ALL_ROLES, can
from tests.conftest import TEST_OWNER_URL, Tenancy
from tests.tenancy_app import build_test_app, running


@pytest.fixture
async def api(tenancy: Tenancy) -> AsyncIterator[AsyncClient]:
    app = build_test_app()
    async with running(app):
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://t") as c:
            yield c


def h(tenancy: Tenancy, user: str, ws: uuid.UUID | str | None = None) -> dict[str, str]:
    headers = {"X-Test-User": str(tenancy.users[user])}
    if ws is not None:
        headers["X-Workspace-Id"] = str(ws)
    return headers


async def test_member_lists_only_own_workspace_rows(api, tenancy):
    r = await api.get("/api/v1/probe", headers=h(tenancy, "a_member", tenancy.ws_a))
    assert r.status_code == 200
    assert r.json() == {"labels": ["a-row"], "role": "member"}


async def test_unauthenticated_is_401(api, tenancy):
    r = await api.get("/api/v1/probe", headers={"X-Workspace-Id": str(tenancy.ws_a)})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthenticated"


async def test_missing_or_malformed_workspace_header_is_400(api, tenancy):
    for headers in (h(tenancy, "a_member"), h(tenancy, "a_member", "not-a-uuid")):
        r = await api.get("/api/v1/probe", headers=headers)
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "workspace_required"


async def test_non_member_gets_the_same_404_as_a_nonexistent_workspace(api, tenancy):
    other = await api.get("/api/v1/probe", headers=h(tenancy, "a_member", tenancy.ws_b))
    ghost = await api.get("/api/v1/probe", headers=h(tenancy, "a_member", uuid.uuid4()))
    assert other.status_code == ghost.status_code == 404
    assert other.json() == ghost.json()  # no existence leak


@pytest.mark.parametrize("user", ["outsider", "a_inactive"])
async def test_non_and_inactive_members_cannot_enter(api, tenancy, user):
    r = await api.get("/api/v1/probe", headers=h(tenancy, user, tenancy.ws_a))
    assert r.status_code == 404


async def test_deactivated_user_account_cannot_enter(api, tenancy):
    engine = create_async_engine(TEST_OWNER_URL)
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE users SET is_active = false WHERE id = :u"),
            {"u": tenancy.users["a_member"]},
        )
    await engine.dispose()
    r = await api.get("/api/v1/probe", headers=h(tenancy, "a_member", tenancy.ws_a))
    assert r.status_code == 404


async def test_soft_deleted_workspace_is_gone(api, tenancy):
    engine = create_async_engine(TEST_OWNER_URL)
    async with engine.begin() as conn:
        await conn.execute(
            text("UPDATE workspaces SET deleted_at = now() WHERE id = :w"), {"w": tenancy.ws_a}
        )
    await engine.dispose()
    r = await api.get("/api/v1/probe", headers=h(tenancy, "a_owner", tenancy.ws_a))
    assert r.status_code == 404


async def test_viewer_cannot_write_member_can(api, tenancy):
    denied = await api.post("/api/v1/probe?label=v", headers=h(tenancy, "a_viewer", tenancy.ws_a))
    assert denied.status_code == 403 and denied.json()["error"]["code"] == "forbidden"
    ok = await api.post("/api/v1/probe?label=m", headers=h(tenancy, "a_member", tenancy.ws_a))
    assert ok.status_code == 200
    seen = await api.get("/api/v1/probe", headers=h(tenancy, "a_owner", tenancy.ws_a))
    assert seen.json()["labels"] == ["a-row", "m"]
    # and workspace B never sees it
    b = await api.get("/api/v1/probe", headers=h(tenancy, "b_owner", tenancy.ws_b))
    assert b.json()["labels"] == ["b-row"]


async def test_failed_request_rolls_back_the_whole_transaction(api, tenancy):
    r = await api.post("/api/v1/probe/boom", headers=h(tenancy, "a_member", tenancy.ws_a))
    assert r.status_code == 500
    seen = await api.get("/api/v1/probe", headers=h(tenancy, "a_member", tenancy.ws_a))
    assert "should-roll-back" not in seen.json()["labels"]


async def test_audit_event_is_written_and_scoped(api, tenancy):
    await api.post("/api/v1/probe?label=audited", headers=h(tenancy, "a_member", tenancy.ws_a))
    mine = await api.get("/api/v1/probe/audit", headers=h(tenancy, "a_owner", tenancy.ws_a))
    events = [e for e in mine.json()["events"] if e["action"] == "probe.created"]
    assert len(events) >= 1 and events[-1]["actor_id"] == str(tenancy.users["a_member"])
    theirs = await api.get("/api/v1/probe/audit", headers=h(tenancy, "b_owner", tenancy.ws_b))
    assert all(e["action"] != "probe.created" for e in theirs.json()["events"])


@pytest.mark.parametrize(
    ("user", "path", "expected"),
    [
        ("a_owner", "/api/v1/probe/audit", 200),
        ("a_admin", "/api/v1/probe/audit", 200),
        ("a_member", "/api/v1/probe/audit", 403),
        ("a_viewer", "/api/v1/probe/audit", 403),
    ],
)
async def test_role_gate_on_activity_read(api, tenancy, user, path, expected):
    r = await api.get(path, headers=h(tenancy, user, tenancy.ws_a))
    assert r.status_code == expected


async def test_only_owner_can_delete_workspace(api, tenancy):
    codes = {}
    for u in ("a_owner", "a_admin", "a_member", "a_viewer"):
        r = await api.delete("/api/v1/probe/workspace", headers=h(tenancy, u, tenancy.ws_a))
        codes[u] = r.status_code
    assert codes == {"a_owner": 200, "a_admin": 403, "a_member": 403, "a_viewer": 403}


# --- RBAC table invariants ---


def test_unknown_action_and_role_are_denied():
    assert not can("owner", "does.not.exist")
    assert not can("superadmin", "workspace.read")


def test_every_action_is_granted_to_owner_and_only_known_roles():
    for action, roles in ACTIONS.items():
        assert "owner" in roles, f"{action} must be allowed for owner"
        assert set(roles) <= set(ALL_ROLES)


def test_viewer_is_read_only():
    writes = [a for a, roles in ACTIONS.items() if "viewer" in roles]
    assert all(a.endswith(".read") or a == "workspace.leave" for a in writes), writes
