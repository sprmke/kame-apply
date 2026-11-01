import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_ai import env, team  # noqa: F401  (env fixture)
from tests.test_workspaces import signup

P = "/api/v1/profiles"


async def make_profile(c, who, ws=None, **kw):
    r = await c.post(P, json={"display_name": "Ana Reyes", **kw}, headers=who.h(ws or who.personal))
    assert r.status_code == 201, r.text
    return r.json()


async def test_first_profile_is_default_and_listing_puts_it_first(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    first = await make_profile(c, me)
    second = await make_profile(c, me, display_name="Second")
    assert first["is_default"] and not second["is_default"]
    assert first["minimization"] == {"photo": False, "dob": False, "full_address": False}
    rows = (await c.get(P, headers=me.h(me.personal))).json()
    assert [r["id"] for r in rows] == [first["id"], second["id"]]


async def test_deleting_the_default_promotes_the_next_profile(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    first = await make_profile(c, me)
    second = await make_profile(c, me, display_name="Second")
    assert (await c.delete(f"{P}/{first['id']}", headers=me.h(me.personal))).status_code == 200
    rows = (await c.get(P, headers=me.h(me.personal))).json()
    assert [r["id"] for r in rows] == [second["id"]] and rows[0]["is_default"]


async def test_profile_update_and_minimization(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    p = await make_profile(c, me)
    r = await c.patch(
        f"{P}/{p['id']}",
        json={
            "headline": "Registered nurse",
            "minimization": {"photo": True, "dob": False, "full_address": False},
        },
        headers=me.h(me.personal),
    )
    assert r.status_code == 200
    assert r.json()["headline"] == "Registered nurse" and r.json()["minimization"]["photo"] is True
    bad = await c.patch(f"{P}/{p['id']}", json={"display_name": None}, headers=me.h(me.personal))
    assert bad.status_code == 422


async def test_experience_with_bullets_roundtrip_and_strength(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await make_profile(c, me)
    exp = (
        await c.post(
            f"{P}/{p['id']}/experiences",
            json={
                "company": "St. Luke's",
                "title": "Registered Nurse",
                "start_date": "2019-03-01",
                "is_current": True,
                "description": "Night shifts, ICU float pool",
            },
            headers=h,
        )
    ).json()
    cases = [
        ("Looked after patients", [], "weak"),
        ("Managed a 12-bed ward", [], "ok"),
        ("Cut medication errors", [{"name": "errors", "change": "-30%"}], "strong"),
    ]
    for text_, metrics, expected in cases:
        r = await c.post(
            f"{P}/{p['id']}/bullets",
            json={"experience_id": exp["id"], "text": text_, "metrics": metrics},
            headers=h,
        )
        assert r.status_code == 201, r.text
        assert r.json()["evidence_strength"] == expected
    full = (await c.get(f"{P}/{p['id']}", headers=h)).json()
    assert [e["company"] for e in full["experiences"]] == ["St. Luke's"]
    assert len(full["bullets"]) == 3


async def test_every_simple_section_supports_crud(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await make_profile(c, me)
    payloads = {
        "education": {"institution": "UP Manila", "degree": "BSN"},
        "projects": {"name": "Ward handover app"},
        "certifications": {"name": "RN licence", "kind": "license", "jurisdiction": "PH"},
        "languages": {"name": "Filipino", "proficiency": "native"},
        "skills": {"name": "IV therapy", "years": 4.5, "last_used": 2025},
    }
    for section, body in payloads.items():
        base = f"{P}/{p['id']}/{section}"
        created = await c.post(base, json=body, headers=h)
        assert created.status_code == 201, (section, created.text)
        item_id = created.json()["id"]
        assert created.json()["source"] == "user"
        patched = await c.patch(f"{base}/{item_id}", json={"do_not_use": True}, headers=h)
        assert patched.status_code == 200 and patched.json()["do_not_use"] is True
        assert len((await c.get(base, headers=h)).json()) == 1
        assert (await c.delete(f"{base}/{item_id}", headers=h)).status_code == 200
        assert (await c.get(base, headers=h)).json() == []
        assert (await c.delete(f"{base}/{item_id}", headers=h)).status_code == 404


@pytest.mark.parametrize(
    "section,body",
    [
        (
            "experiences",
            {"company": "A", "title": "B", "start_date": "2022-01-01", "end_date": "2021-01-01"},
        ),
        (
            "experiences",
            {"company": "A", "title": "B", "is_current": True, "end_date": "2022-01-01"},
        ),
        ("experiences", {"company": "", "title": "B"}),
        ("bullets", {"text": "no parent"}),
        ("skills", {"name": "x", "years": -1}),
        ("certifications", {"name": "x", "kind": "badge"}),
        ("education", {"institution": "x", "source": "robot"}),
    ],
)
async def test_invalid_entries_are_rejected(env, section, body):  # noqa: F811
    c, _ = env
    me = await signup(c)
    p = await make_profile(c, me)
    r = await c.post(f"{P}/{p['id']}/{section}", json=body, headers=me.h(me.personal))
    assert r.status_code == 422


async def test_patch_revalidates_the_merged_row(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await make_profile(c, me)
    exp = (
        await c.post(
            f"{P}/{p['id']}/experiences",
            json={"company": "A", "title": "B", "start_date": "2022-01-01"},
            headers=h,
        )
    ).json()
    r = await c.patch(
        f"{P}/{p['id']}/experiences/{exp['id']}", json={"end_date": "2021-01-01"}, headers=h
    )
    assert r.status_code == 422
    r = await c.patch(f"{P}/{p['id']}/experiences/{exp['id']}", json={"company": ""}, headers=h)
    assert r.status_code == 422


async def test_bullet_parent_must_belong_to_the_same_profile(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    a = await make_profile(c, me)
    b = await make_profile(c, me, display_name="B")
    exp_b = (
        await c.post(f"{P}/{b['id']}/experiences", json={"company": "A", "title": "B"}, headers=h)
    ).json()
    r = await c.post(
        f"{P}/{a['id']}/bullets", json={"experience_id": exp_b["id"], "text": "x"}, headers=h
    )
    assert r.status_code == 404
    r = await c.post(
        f"{P}/{a['id']}/bullets", json={"experience_id": str(uuid.uuid4()), "text": "x"}, headers=h
    )
    assert r.status_code == 404


async def test_deleting_an_experience_removes_its_bullets(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await make_profile(c, me)
    exp = (
        await c.post(f"{P}/{p['id']}/experiences", json={"company": "A", "title": "B"}, headers=h)
    ).json()
    await c.post(
        f"{P}/{p['id']}/bullets",
        json={"experience_id": exp["id"], "text": "did 3 things"},
        headers=h,
    )
    await c.delete(f"{P}/{p['id']}/experiences/{exp['id']}", headers=h)
    assert (await c.get(f"{P}/{p['id']}/bullets", headers=h)).json() == []


async def test_roles_viewer_reads_member_writes(env):  # noqa: F811
    c, outbox = env
    owner, ws, people = await team(c, outbox)
    p = await make_profile(c, owner, ws)
    for key in ("v",):
        who = people[key]
        assert (await c.get(P, headers=who.h(ws))).status_code == 200
        assert (await c.get(f"{P}/{p['id']}", headers=who.h(ws))).status_code == 200
        assert (await c.post(P, json={"display_name": "x"}, headers=who.h(ws))).status_code == 403
        assert (
            await c.patch(f"{P}/{p['id']}", json={"headline": "x"}, headers=who.h(ws))
        ).status_code == 403
        assert (await c.delete(f"{P}/{p['id']}", headers=who.h(ws))).status_code == 403
    r = await c.post(f"{P}/{p['id']}/skills", json={"name": "Python"}, headers=people["m"].h(ws))
    assert r.status_code == 201


async def test_cross_tenant_isolation_on_every_route(env):  # noqa: F811
    c, _ = env
    alice, mallory = await signup(c), await signup(c)
    p = await make_profile(c, alice)
    exp = (
        await c.post(
            f"{P}/{p['id']}/experiences",
            json={"company": "Secret Co", "title": "CTO"},
            headers=alice.h(alice.personal),
        )
    ).json()
    # Mallory cannot name Alice's workspace at all.
    assert (await c.get(P, headers=mallory.h(alice.personal))).status_code == 404
    # Inside her own workspace Alice's ids simply do not exist.
    mh = mallory.h(mallory.personal)
    assert (await c.get(P, headers=mh)).json() == []
    assert (await c.get(f"{P}/{p['id']}", headers=mh)).status_code == 404
    assert (
        await c.patch(f"{P}/{p['id']}", json={"headline": "pwn"}, headers=mh)
    ).status_code == 404
    assert (await c.delete(f"{P}/{p['id']}", headers=mh)).status_code == 404
    mine = await make_profile(c, mallory)
    base = f"{P}/{mine['id']}/experiences"
    assert (
        await c.patch(f"{base}/{exp['id']}", json={"company": "x"}, headers=mh)
    ).status_code == 404
    assert (await c.delete(f"{base}/{exp['id']}", headers=mh)).status_code == 404
    # A bullet cannot attach to another workspace's experience.
    r = await c.post(
        f"{P}/{mine['id']}/bullets", json={"experience_id": exp["id"], "text": "x"}, headers=mh
    )
    assert r.status_code == 404
    assert (await c.get(f"{P}/{p['id']}/experiences", headers=mh)).status_code == 404
    # Alice's data is untouched.
    full = (await c.get(f"{P}/{p['id']}", headers=alice.h(alice.personal))).json()
    assert full["headline"] is None and full["experiences"][0]["company"] == "Secret Co"


async def test_rls_hides_profile_rows_without_a_workspace(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    p = await make_profile(c, me)
    await c.post(f"{P}/{p['id']}/skills", json={"name": "Python"}, headers=me.h(me.personal))
    engine = create_async_engine(TEST_DB_URL)
    try:
        async with engine.begin() as conn:
            for sql in (
                "SELECT count(*) FROM candidate_profiles",
                "SELECT count(*) FROM profile_skills",
            ):
                assert (await conn.execute(text(sql))).scalar_one() == 0, sql
    finally:
        await engine.dispose()


async def test_audit_rows_carry_ids_and_field_names_never_content(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await make_profile(c, me)
    await c.patch(f"{P}/{p['id']}", json={"summary": "CONFIDENTIAL-SUMMARY-TEXT"}, headers=h)
    exp = (
        await c.post(
            f"{P}/{p['id']}/experiences", json={"company": "SecretCo", "title": "T"}, headers=h
        )
    ).json()
    await c.post(
        f"{P}/{p['id']}/bullets",
        json={"experience_id": exp["id"], "text": "BULLET-BODY-TEXT 40%"},
        headers=h,
    )
    engine = create_async_engine(TEST_OWNER_URL)
    try:
        async with engine.begin() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT action, after::text FROM activity_log WHERE action LIKE 'profile.%' "
                        "AND workspace_id = :w ORDER BY created_at"
                    ),
                    {"w": uuid.UUID(me.personal)},
                )
            ).all()
    finally:
        await engine.dispose()
    actions = [r[0] for r in rows]
    assert actions == [
        "profile.created",
        "profile.updated",
        "profile.experiences.created",
        "profile.bullets.created",
    ]
    blob = " ".join(r[1] or "" for r in rows)
    assert "CONFIDENTIAL" not in blob and "SecretCo" not in blob and "BULLET-BODY" not in blob
    assert "summary" in blob
