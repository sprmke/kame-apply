"""Phase 13: extension tokens, clip, plan-page, platform policies, cross-tenant."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.extension.brain import plan_fields
from app.extension.schemas import ExtractedField
from app.extension.tokens import hash_token, looks_like_extension_token
from tests.conftest import TEST_OWNER_URL
from tests.test_profiles import make_profile
from tests.test_workspaces import signup

pytest_plugins = ["tests.test_workspaces"]

E = "/api/v1/extension"


async def test_brain_sensitive_and_fill():
    fields = [
        ExtractedField(id="a#0", label="First name", name="first_name", type="text"),
        ExtractedField(id="b#1", label="Social Security Number", name="ssn", type="text"),
        ExtractedField(id="c#2", label="Email", name="email", type="email", autocomplete="email"),
    ]
    instr, restricted, _ = plan_fields(
        fields=fields,
        profile={"display_name": "Ada Lovelace", "email": "ada@example.com"},
        answers={},
        autofill_allowed=True,
    )
    assert not restricted
    by_id = {i.field_id: i for i in instr}
    assert by_id["a#0"].action == "fill" and by_id["a#0"].value == "Ada"
    assert by_id["b#1"].action == "checkpoint"
    assert by_id["c#2"].action == "fill" and by_id["c#2"].value == "ada@example.com"


async def test_brain_platform_policy_blocks():
    fields = [ExtractedField(id="a#0", label="First name", type="text")]
    instr, _, notes = plan_fields(
        fields=fields,
        profile={"display_name": "Ada"},
        answers={},
        autofill_allowed=False,
    )
    assert instr[0].action == "skip"
    assert notes


async def test_extension_token_clip_plan_and_policy(env):
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await make_profile(c, me)
    track = await c.post(
        "/api/v1/tracks",
        json={
            "name": "SWE",
            "profile_id": p["id"],
            "nl_text": "software engineer",
            "criteria": {
                "schema_version": 1,
                "titles": [{"title": "Software Engineer", "synonyms": [], "exclude": False}],
            },
        },
        headers=h,
    )
    assert track.status_code == 201, track.text
    tid = track.json()["id"]

    created = await c.post(f"{E}/tokens", json={"label": "browser"}, headers=h)
    assert created.status_code == 201, created.text
    raw = created.json()["token"]
    assert looks_like_extension_token(raw)
    tok_id = created.json()["id"]

    listed = await c.get(f"{E}/tokens", headers=h)
    assert listed.status_code == 200
    assert any(t["id"] == tok_id for t in listed.json())

    ext_h = {
        "Authorization": f"Bearer {raw}",
        "X-Workspace-Id": me.personal,
    }
    sess = await c.get(f"{E}/session", headers=ext_h)
    assert sess.status_code == 200, sess.text
    assert sess.json()["workspace_id"] == me.personal

    clip = await c.post(
        f"{E}/clip",
        json={
            "url": "https://boards.greenhouse.io/acme/jobs/123",
            "title": "Engineer",
            "company": "Acme",
            "description_text": "Build things",
            "track_id": tid,
            "platform": "greenhouse",
        },
        headers=ext_h,
    )
    assert clip.status_code == 201, clip.text
    job_id = clip.json()["job_id"]
    assert clip.json()["track_job_id"]

    plan = await c.post(
        f"{E}/runs/plan-page",
        json={
            "profile_id": p["id"],
            "track_id": tid,
            "job_id": job_id,
            "platform": "greenhouse",
            "page_url": "https://boards.greenhouse.io/acme/jobs/123/application",
            "fields": [
                {"id": "fn#0", "label": "First Name", "name": "first_name", "type": "text"},
                {"id": "ssn#1", "label": "SSN", "name": "ssn", "type": "text", "required": True},
            ],
        },
        headers=ext_h,
    )
    assert plan.status_code == 200, plan.text
    body = plan.json()
    assert body["autofill_allowed"] is True
    actions = {i["field_id"]: i["action"] for i in body["instructions"]}
    assert actions["fn#0"] == "fill"
    assert actions["ssn#1"] == "checkpoint"

    # LinkedIn autofill off by default
    li = await c.post(
        f"{E}/runs/plan-page",
        json={
            "profile_id": p["id"],
            "platform": "linkedin",
            "page_url": "https://www.linkedin.com/jobs/view/1",
            "fields": [{"id": "fn#0", "label": "First Name", "type": "text"}],
        },
        headers=ext_h,
    )
    assert li.status_code == 200
    assert li.json()["autofill_allowed"] is False
    assert all(i["action"] == "skip" for i in li.json()["instructions"])

    # Opt-in requires terms
    bad = await c.put(
        f"{E}/platform-policies",
        json={"platform": "linkedin", "autofill_enabled": True, "acknowledge_terms": False},
        headers=h,
    )
    assert bad.status_code == 422

    ok = await c.put(
        f"{E}/platform-policies",
        json={"platform": "linkedin", "autofill_enabled": True, "acknowledge_terms": True},
        headers=h,
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["autofill_enabled"] is True

    li2 = await c.post(
        f"{E}/runs/plan-page",
        json={
            "profile_id": p["id"],
            "platform": "linkedin",
            "page_url": "https://www.linkedin.com/jobs/view/1",
            "fields": [{"id": "fn#0", "label": "First Name", "type": "text"}],
        },
        headers=ext_h,
    )
    assert li2.json()["autofill_allowed"] is True

    await c.post(f"{E}/tokens/{tok_id}/revoke", headers=h)
    denied = await c.get(f"{E}/session", headers=ext_h)
    assert denied.status_code == 401

    engine = create_async_engine(TEST_OWNER_URL)
    async with engine.begin() as conn:
        row = (
            await conn.execute(
                text("SELECT token_hash, revoked_at FROM extension_tokens WHERE id = :id"),
                {"id": tok_id},
            )
        ).first()
        assert row is not None and row[1] is not None
        assert row[0] == hash_token(raw)
    await engine.dispose()


async def test_extension_cross_tenant_token(env):
    c, _ = env
    a = await signup(c)
    b = await signup(c)
    ha = a.h(a.personal)
    tok = await c.post(f"{E}/tokens", json={"label": "x"}, headers=ha)
    raw = tok.json()["token"]
    # Token for A cannot use B's workspace header
    r = await c.get(
        f"{E}/session",
        headers={"Authorization": f"Bearer {raw}", "X-Workspace-Id": b.personal},
    )
    assert r.status_code == 403


async def test_extension_rls_probe(tenancy):
    engine = create_async_engine(TEST_OWNER_URL)
    async with engine.begin() as conn:
        # Seed a token in ws_a
        tid = uuid.uuid4()
        await conn.execute(
            text(
                "INSERT INTO extension_tokens (id, workspace_id, user_id, token_hash, label) "
                "VALUES (:id, :w, :u, :h, 't')"
            ),
            {
                "id": tid,
                "w": tenancy.ws_a,
                "u": tenancy.users["a_owner"],
                "h": hash_token("ka_ext_probe"),
            },
        )
        await conn.execute(
            text(
                "SELECT set_config('app.user_id', :u, true), set_config('app.workspace_id', :w, true)"
            ),
            {"u": str(tenancy.users["b_owner"]), "w": str(tenancy.ws_b)},
        )
        # Switch to app role for RLS check
        await conn.execute(text("SET LOCAL ROLE kame_apply_app"))
        n = (
            await conn.execute(
                text("SELECT count(*) FROM extension_tokens WHERE id = :id"),
                {"id": tid},
            )
        ).scalar_one()
        assert n == 0
    await engine.dispose()
