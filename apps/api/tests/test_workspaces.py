import re
import uuid

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
async def env():
    settings = Settings(
        database_url=TEST_DB_URL, environment="test", log_json=False, auth_rate_limit_enabled=False
    )
    app = create_app(settings)
    app.state.mailer = Outbox()
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c, app.state.mailer


def last_token(outbox: Outbox) -> str:
    found = re.search(r"token=([\w-]+)", outbox.sent[-1].text)
    assert found
    return found.group(1)


class Who:
    def __init__(self, email: str, token: str, user_id: str, ws: str):
        self.email, self.token, self.id, self.personal = email, token, user_id, ws

    def h(self, ws: str | None = None) -> dict[str, str]:
        h = {"Authorization": f"Bearer {self.token}"}
        if ws:
            h["X-Workspace-Id"] = ws
        return h


async def verify_in_db(email: str) -> None:
    e = create_async_engine(TEST_OWNER_URL)
    async with e.begin() as conn:
        await conn.execute(
            text("UPDATE users SET email_verified_at = now() WHERE email = :e"), {"e": email}
        )
    await e.dispose()


async def signup(c, *, verified: bool = True) -> Who:
    """Registers a user. Verified by default: inviting and accepting invites need a confirmed email."""
    email = f"w-{uuid.uuid4().hex[:10]}@example.com"
    r = await c.post("/api/v1/auth/register", json={"email": email, "password": PW})
    assert r.status_code == 201, r.text
    if verified:
        await verify_in_db(email)
    body = r.json()
    me = Who(email, body["access_token"], body["user"]["id"], "")
    wss = (await c.get("/api/v1/workspaces", headers=me.h())).json()
    me.personal = wss[0]["id"]
    return me


async def team_with(c, owner: Who, outbox, members: dict[str, str]) -> tuple[str, dict[str, Who]]:
    """Create a team workspace owned by `owner` and join users with the given roles."""
    ws = (await c.post("/api/v1/workspaces", json={"name": "Team"}, headers=owner.h())).json()["id"]
    people = {}
    for name, role in members.items():
        p = await signup(c)
        people[name] = p
        r = await c.post(
            "/api/v1/workspace/invitations",
            json={"email": p.email, "role": role},
            headers=owner.h(ws),
        )
        assert r.status_code == 201, r.text
        tok = last_token(outbox)
        a = await c.post("/api/v1/invitations/accept", json={"token": tok}, headers=p.h())
        assert a.status_code == 200, a.text
    return ws, people


async def test_signup_creates_a_personal_workspace_owned_by_the_user(env):
    c, _ = env
    me = await signup(c)
    wss = (await c.get("/api/v1/workspaces", headers=me.h())).json()
    assert [(w["kind"], w["role"], w["name"]) for w in wss] == [("personal", "owner", "Personal")]
    e = create_async_engine(TEST_OWNER_URL)
    async with e.connect() as conn:
        n = (
            await conn.execute(
                text(
                    "SELECT count(*) FROM activity_log WHERE workspace_id=:w AND action='workspace.created'"
                ),
                {"w": uuid.UUID(me.personal)},
            )
        ).scalar_one()
    await e.dispose()
    assert n == 1


async def test_users_only_see_their_own_workspaces(env):
    c, _ = env
    a, b = await signup(c), await signup(c)
    assert [w["id"] for w in (await c.get("/api/v1/workspaces", headers=b.h())).json()] == [
        b.personal
    ]
    # Another user's workspace id is indistinguishable from a missing one.
    r = await c.get("/api/v1/workspace", headers=b.h(a.personal))
    ghost = await c.get("/api/v1/workspace", headers=b.h(str(uuid.uuid4())))
    assert r.status_code == ghost.status_code == 404 and r.json() == ghost.json()


async def test_rename_requires_manager_and_is_audited(env):
    c, outbox = env
    owner = await signup(c)
    ws, p = await team_with(c, owner, outbox, {"m": "member", "ad": "admin"})
    assert (
        await c.patch("/api/v1/workspace", json={"name": "X"}, headers=p["m"].h(ws))
    ).status_code == 403
    ok = await c.patch("/api/v1/workspace", json={"name": "Renamed"}, headers=p["ad"].h(ws))
    assert ok.status_code == 200 and ok.json()["name"] == "Renamed"
    bad = await c.patch("/api/v1/workspace", json={"name": "a\nb"}, headers=owner.h(ws))
    assert bad.status_code == 422


async def test_role_changes_respect_rank(env):
    c, outbox = env
    owner = await signup(c)
    ws, p = await team_with(c, owner, outbox, {"ad": "admin", "m": "member", "v": "viewer"})

    def patch(actor, target, role):
        return c.patch(
            f"/api/v1/workspace/members/{target.id}", json={"role": role}, headers=actor.h(ws)
        )

    assert (await patch(p["ad"], p["v"], "member")).status_code == 200
    assert (await patch(p["ad"], p["m"], "admin")).status_code == 403  # cannot grant own level
    assert (await patch(p["ad"], owner, "viewer")).status_code == 403  # cannot touch the owner
    assert (await patch(p["m"], p["v"], "admin")).status_code == 403  # members cannot manage
    assert (await patch(owner, p["ad"], "member")).status_code == 200
    assert (await patch(owner, owner, "admin")).status_code == 403  # not yourself
    bad = await c.patch(
        f"/api/v1/workspace/members/{p['m'].id}", json={"role": "owner"}, headers=owner.h(ws)
    )
    assert bad.status_code == 422  # ownership moves only via transfer


async def test_remove_member_rules(env):
    c, outbox = env
    owner = await signup(c)
    ws, p = await team_with(c, owner, outbox, {"ad": "admin", "m": "member"})

    def rm(actor, target):
        return c.delete(f"/api/v1/workspace/members/{target.id}", headers=actor.h(ws))

    assert (await rm(p["ad"], owner)).status_code == 403
    assert (await rm(p["m"], p["ad"])).status_code == 403
    assert (await rm(p["ad"], p["m"])).status_code == 200
    # Removed members lose access immediately (same 404 as a stranger).
    assert (await c.get("/api/v1/workspace", headers=p["m"].h(ws))).status_code == 404
    assert (await rm(owner, p["m"])).status_code == 404


async def test_leave_and_last_owner_protection(env):
    c, outbox = env
    owner = await signup(c)
    ws, p = await team_with(c, owner, outbox, {"m": "member"})
    assert (await c.post("/api/v1/workspace/leave", headers=owner.h(ws))).json()["error"][
        "code"
    ] == "owner_must_transfer"
    assert (await c.post("/api/v1/workspace/leave", headers=owner.h(owner.personal))).json()[
        "error"
    ]["code"] == "personal_workspace"
    assert (await c.post("/api/v1/workspace/leave", headers=p["m"].h(ws))).status_code == 200
    assert (await c.get("/api/v1/workspace", headers=p["m"].h(ws))).status_code == 404


async def test_transfer_ownership_then_old_owner_can_leave(env):
    c, outbox = env
    owner = await signup(c)
    ws, p = await team_with(c, owner, outbox, {"ad": "admin", "m": "member"})
    assert (
        await c.post(
            "/api/v1/workspace/transfer", json={"user_id": p["ad"].id}, headers=p["ad"].h(ws)
        )
    ).status_code == 403
    assert (
        await c.post(
            "/api/v1/workspace/transfer", json={"user_id": str(uuid.uuid4())}, headers=owner.h(ws)
        )
    ).status_code == 404
    assert (
        await c.post(
            "/api/v1/workspace/transfer", json={"user_id": p["ad"].id}, headers=owner.h(ws)
        )
    ).status_code == 200
    roles = {
        m["email"]: m["role"]
        for m in (await c.get("/api/v1/workspace/members", headers=owner.h(ws))).json()
    }
    assert roles[owner.email] == "admin" and roles[p["ad"].email] == "owner"
    assert (await c.post("/api/v1/workspace/leave", headers=owner.h(ws))).status_code == 200


async def test_delete_workspace_is_owner_only_and_hides_it(env):
    c, outbox = env
    owner = await signup(c)
    ws, p = await team_with(c, owner, outbox, {"ad": "admin"})
    assert (await c.delete("/api/v1/workspace", headers=p["ad"].h(ws))).status_code == 403
    assert (await c.delete("/api/v1/workspace", headers=owner.h(owner.personal))).json()["error"][
        "code"
    ] == "personal_workspace"
    assert (await c.delete("/api/v1/workspace", headers=owner.h(ws))).status_code == 200
    assert (await c.get("/api/v1/workspace", headers=owner.h(ws))).status_code == 404
    assert ws not in [
        w["id"] for w in (await c.get("/api/v1/workspaces", headers=owner.h())).json()
    ]


async def test_team_workspace_limit(env):
    c, _ = env
    me = await signup(c)
    for _ in range(5):
        assert (
            await c.post("/api/v1/workspaces", json={"name": "T"}, headers=me.h())
        ).status_code == 201
    r = await c.post("/api/v1/workspaces", json={"name": "T"}, headers=me.h())
    assert r.status_code == 409 and r.json()["error"]["code"] == "workspace_limit"


async def test_invitation_flow_and_single_use(env):
    c, outbox = env
    owner, guest = await signup(c), await signup(c)
    ws = (await c.post("/api/v1/workspaces", json={"name": "Crew"}, headers=owner.h())).json()["id"]
    r = await c.post(
        "/api/v1/workspace/invitations",
        json={"email": guest.email.upper(), "role": "viewer"},
        headers=owner.h(ws),
    )
    assert r.status_code == 201
    assert outbox.sent[-1].to == guest.email and "Crew" in outbox.sent[-1].subject
    assert len((await c.get("/api/v1/workspace/invitations", headers=owner.h(ws))).json()) == 1
    tok = last_token(outbox)
    ok = await c.post("/api/v1/invitations/accept", json={"token": tok}, headers=guest.h())
    assert ok.status_code == 200 and ok.json()["role"] == "viewer" and ok.json()["id"] == ws
    assert (await c.get("/api/v1/workspace", headers=guest.h(ws))).json()["role"] == "viewer"
    again = await c.post("/api/v1/invitations/accept", json={"token": tok}, headers=guest.h())
    assert again.status_code == 400 and again.json()["error"]["code"] == "invalid_invitation"
    assert (await c.get("/api/v1/workspace/invitations", headers=owner.h(ws))).json() == []
    dup = await c.post(
        "/api/v1/workspace/invitations", json={"email": guest.email}, headers=owner.h(ws)
    )
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "already_member"


async def test_invitation_is_bound_to_the_invited_email(env):
    c, outbox = env
    owner, invited, thief = await signup(c), await signup(c), await signup(c)
    ws = (await c.post("/api/v1/workspaces", json={"name": "Crew"}, headers=owner.h())).json()["id"]
    await c.post(
        "/api/v1/workspace/invitations", json={"email": invited.email}, headers=owner.h(ws)
    )
    tok = last_token(outbox)
    r = await c.post("/api/v1/invitations/accept", json={"token": tok}, headers=thief.h())
    assert r.status_code == 403 and r.json()["error"]["code"] == "invite_email_mismatch"
    assert (await c.get("/api/v1/workspace", headers=thief.h(ws))).status_code == 404
    assert (
        await c.post("/api/v1/invitations/accept", json={"token": tok}, headers=invited.h())
    ).status_code == 200


async def test_reinviting_voids_the_old_link_and_revoke_works(env):
    c, outbox = env
    owner, guest = await signup(c), await signup(c)
    ws = (await c.post("/api/v1/workspaces", json={"name": "Crew"}, headers=owner.h())).json()["id"]
    await c.post("/api/v1/workspace/invitations", json={"email": guest.email}, headers=owner.h(ws))
    old = last_token(outbox)
    await c.post("/api/v1/workspace/invitations", json={"email": guest.email}, headers=owner.h(ws))
    assert (
        await c.post("/api/v1/invitations/accept", json={"token": old}, headers=guest.h())
    ).status_code == 400
    pending = (await c.get("/api/v1/workspace/invitations", headers=owner.h(ws))).json()
    assert len(pending) == 1
    assert (
        await c.delete(f"/api/v1/workspace/invitations/{pending[0]['id']}", headers=owner.h(ws))
    ).status_code == 200
    new = last_token(outbox)
    assert (
        await c.post("/api/v1/invitations/accept", json={"token": new}, headers=guest.h())
    ).status_code == 400


async def test_expired_invitation_is_rejected(env):
    c, outbox = env
    owner, guest = await signup(c), await signup(c)
    ws = (await c.post("/api/v1/workspaces", json={"name": "Crew"}, headers=owner.h())).json()["id"]
    await c.post("/api/v1/workspace/invitations", json={"email": guest.email}, headers=owner.h(ws))
    tok = last_token(outbox)
    e = create_async_engine(TEST_OWNER_URL)
    async with e.begin() as conn:
        await conn.execute(
            text(
                "UPDATE invitations SET expires_at = now() - interval '1 minute' WHERE workspace_id=:w"
            ),
            {"w": uuid.UUID(ws)},
        )
    await e.dispose()
    assert (
        await c.post("/api/v1/invitations/accept", json={"token": tok}, headers=guest.h())
    ).status_code == 400


async def test_invite_rank_limits(env):
    c, outbox = env
    owner = await signup(c)
    ws, p = await team_with(c, owner, outbox, {"ad": "admin", "m": "member"})

    def inv(actor, role):
        return c.post(
            "/api/v1/workspace/invitations",
            json={"email": "x@example.com", "role": role},
            headers=actor.h(ws),
        )

    assert (await inv(p["m"], "viewer")).status_code == 403
    assert (await inv(p["ad"], "admin")).status_code == 403
    assert (await inv(p["ad"], "member")).status_code == 201
    assert (await inv(owner, "admin")).status_code == 201
    assert (await inv(owner, "owner")).status_code == 422


async def test_invitation_rls_hides_other_workspaces_invites_without_the_token(env):
    c, _ = env
    a, b = await signup(c), await signup(c)
    wa = (await c.post("/api/v1/workspaces", json={"name": "A"}, headers=a.h())).json()["id"]
    wb = (await c.post("/api/v1/workspaces", json={"name": "B"}, headers=b.h())).json()["id"]
    await c.post("/api/v1/workspace/invitations", json={"email": "p@example.com"}, headers=a.h(wa))
    assert (await c.get("/api/v1/workspace/invitations", headers=b.h(wb))).json() == []
    assert (await c.get("/api/v1/workspace/invitations", headers=b.h(wa))).status_code == 404


async def test_invitations_table_is_invisible_to_the_app_role_without_context(env):
    c, outbox = env
    owner, guest = await signup(c), await signup(c)
    ws = (await c.post("/api/v1/workspaces", json={"name": "Crew"}, headers=owner.h())).json()["id"]
    await c.post("/api/v1/workspace/invitations", json={"email": guest.email}, headers=owner.h(ws))
    tok = last_token(outbox)
    from app.auth.tokens import hash_token

    e = create_async_engine(TEST_DB_URL)  # the RLS-restricted app role
    async with e.begin() as conn:
        none = (await conn.execute(text("SELECT count(*) FROM invitations"))).scalar_one()
        await conn.execute(
            text("SELECT set_config('app.workspace_id', :w, true)"), {"w": str(uuid.uuid4())}
        )
        wrong_ws = (await conn.execute(text("SELECT count(*) FROM invitations"))).scalar_one()
        await conn.execute(
            text("SELECT set_config('app.invite_token_hash', :h, true)"), {"h": hash_token(tok)}
        )
        by_token = (await conn.execute(text("SELECT count(*) FROM invitations"))).scalar_one()
    await e.dispose()
    assert (none, wrong_ws, by_token) == (0, 0, 1)


async def test_member_list_excludes_the_callers_memberships_in_other_workspaces(env):
    # RLS lets a user see their own membership rows everywhere (needed to resolve the active
    # workspace), so every membership query must also filter by workspace explicitly.
    c, outbox = env
    owner = await signup(c)
    ws, _ = await team_with(c, owner, outbox, {"m": "member"})
    members = (await c.get("/api/v1/workspace/members", headers=owner.h(ws))).json()
    assert len(members) == 2
    personal = (await c.get("/api/v1/workspace/members", headers=owner.h(owner.personal))).json()
    assert len(personal) == 1
