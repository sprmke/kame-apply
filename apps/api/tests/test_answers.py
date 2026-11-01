"""Answer bank CRUD, quick setup, sensitive guard, audit, and cross-tenant isolation."""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_ai import env  # noqa: F401
from tests.test_profiles import make_profile
from tests.test_workspaces import signup

P = "/api/v1/profiles"


async def test_canonical_keys_and_setup_seeds_defaults(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await make_profile(
        c,
        me,
        links=[
            {"label": "LinkedIn", "url": "https://linkedin.com/in/ana"},
            {"label": "GitHub", "url": "https://github.com/ana"},
        ],
    )
    keys = (await c.get(f"{P}/{p['id']}/answers/keys", headers=h)).json()
    assert {k["key"] for k in keys} >= {
        "work_authorization",
        "sponsorship",
        "notice_period",
        "salary_expectation",
        "relocation",
        "remote_preference",
        "eeo_race",
        "eeo_gender",
        "eeo_veteran",
        "eeo_disability",
        "how_did_you_hear",
        "linkedin_url",
        "portfolio_url",
        "github_url",
    }
    wa = next(k for k in keys if k["key"] == "work_authorization")
    assert wa["country_scoped"] is True

    setup = await c.post(
        f"{P}/{p['id']}/answers/setup",
        json={"countries": ["US", "PH"]},
        headers=h,
    )
    assert setup.status_code == 200, setup.text
    body = setup.json()
    assert body["created"] > 0 and body["skipped"] == 0

    rows = (await c.get(f"{P}/{p['id']}/answers", headers=h)).json()
    by_key = {}
    for r in rows:
        by_key.setdefault(r["key"], []).append(r)

    assert len(by_key["work_authorization"]) == 2
    assert {r["country"] for r in by_key["work_authorization"]} == {"US", "PH"}
    assert by_key["sponsorship"][0]["answer"] == "No"
    assert by_key["sponsorship"][0]["approved"] is False
    eeo = by_key["eeo_race"][0]
    assert eeo["answer"] == "Decline to self-identify" and eeo["approved"] is True
    assert by_key["linkedin_url"][0]["answer"] == "https://linkedin.com/in/ana"
    assert by_key["github_url"][0]["answer"] == "https://github.com/ana"

    # Idempotent: second setup skips existing slots.
    again = (
        await c.post(f"{P}/{p['id']}/answers/setup", json={"countries": ["US"]}, headers=h)
    ).json()
    assert again["created"] == 0 and again["skipped"] > 0


async def test_answer_crud_scope_search_and_duplicate(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await make_profile(c, me)
    track_body = (
        await c.post(
            "/api/v1/tracks",
            json={
                "profile_id": p["id"],
                "name": "Answer scope track",
                "criteria": {
                    "titles": [{"title": "Engineer", "synonyms": [], "exclude": False}],
                },
            },
            headers=h,
        )
    ).json()
    track = uuid.UUID(track_body["id"])

    created = await c.post(
        f"{P}/{p['id']}/answers",
        json={
            "key": "sponsorship",
            "answer": "No sponsorship needed",
            "question_variants": ["Need visa sponsorship?"],
            "approved": True,
        },
        headers=h,
    )
    assert created.status_code == 201, created.text
    ans = created.json()
    assert ans["key"] == "sponsorship" and ans["scope"] == "global" and ans["approved"] is True

    dup = await c.post(
        f"{P}/{p['id']}/answers",
        json={"key": "sponsorship", "answer": "Yes"},
        headers=h,
    )
    assert dup.status_code == 409

    # Country required for work_authorization.
    bad = await c.post(
        f"{P}/{p['id']}/answers",
        json={"key": "work_authorization", "answer": "Citizen"},
        headers=h,
    )
    assert bad.status_code == 422

    wa = (
        await c.post(
            f"{P}/{p['id']}/answers",
            json={"key": "work_authorization", "country": "US", "answer": "Citizen"},
            headers=h,
        )
    ).json()
    assert wa["country"] == "US"
    assert wa["question_variants"]  # seeded from catalog

    track_row = await c.post(
        f"{P}/{p['id']}/answers",
        json={
            "key": "salary_expectation",
            "answer": "120000 USD",
            "scope": "track",
            "track_id": str(track),
            "answer_json": {"amount": 120000, "currency": "USD", "period": "year"},
        },
        headers=h,
    )
    assert track_row.status_code == 201, track_row.text

    listed = (await c.get(f"{P}/{p['id']}/answers", params={"q": "visa"}, headers=h)).json()
    assert [r["id"] for r in listed] == [ans["id"]]

    scoped = (
        await c.get(
            f"{P}/{p['id']}/answers",
            params={"scope": "track", "track_id": str(track)},
            headers=h,
        )
    ).json()
    assert len(scoped) == 1 and scoped[0]["key"] == "salary_expectation"

    patched = await c.patch(
        f"{P}/{p['id']}/answers/{ans['id']}",
        json={"answer": "No", "approved": True},
        headers=h,
    )
    assert patched.status_code == 200 and patched.json()["answer"] == "No"

    assert (await c.delete(f"{P}/{p['id']}/answers/{ans['id']}", headers=h)).status_code == 200
    assert (await c.get(f"{P}/{p['id']}/answers/{ans['id']}", headers=h)).status_code == 404


async def test_rejects_sensitive_numbers_in_answers(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await make_profile(c, me)
    r = await c.post(
        f"{P}/{p['id']}/answers",
        json={"key": "custom_note", "answer": "My SSN is 123-45-6789"},
        headers=h,
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "sensitive_content"


async def test_cross_tenant_answers_are_404(env):  # noqa: F811
    c, _ = env
    alice, mallory = await signup(c), await signup(c)
    p = await make_profile(c, alice)
    ans = (
        await c.post(
            f"{P}/{p['id']}/answers",
            json={"key": "relocation", "answer": "Open to relocate"},
            headers=alice.h(alice.personal),
        )
    ).json()
    mh = mallory.h(mallory.personal)
    mine = await make_profile(c, mallory)
    assert (await c.get(f"{P}/{p['id']}/answers", headers=mh)).status_code == 404
    assert (await c.get(f"{P}/{p['id']}/answers/keys", headers=mh)).status_code == 404
    assert (await c.get(f"{P}/{p['id']}/answers/{ans['id']}", headers=mh)).status_code == 404
    assert (await c.delete(f"{P}/{mine['id']}/answers/{ans['id']}", headers=mh)).status_code == 404
    assert (
        await c.get(f"{P}/{p['id']}/answers/{ans['id']}", headers=alice.h(alice.personal))
    ).status_code == 200


async def test_rls_hides_answers_without_workspace(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    p = await make_profile(c, me)
    await c.post(
        f"{P}/{p['id']}/answers",
        json={"key": "notice_period", "answer": "2 weeks"},
        headers=me.h(me.personal),
    )
    engine = create_async_engine(TEST_DB_URL)
    try:
        async with engine.begin() as conn:
            assert (await conn.execute(text("SELECT count(*) FROM answer_bank"))).scalar_one() == 0
    finally:
        await engine.dispose()


async def test_audit_never_stores_answer_text(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await make_profile(c, me)
    marker = "UNIQUE-ANSWER-BODY-QQ7"
    ans = (
        await c.post(
            f"{P}/{p['id']}/answers",
            json={"key": "how_did_you_hear", "answer": marker, "approved": True},
            headers=h,
        )
    ).json()
    await c.patch(
        f"{P}/{p['id']}/answers/{ans['id']}",
        json={"answer": f"{marker}-edited"},
        headers=h,
    )
    engine = create_async_engine(TEST_OWNER_URL)
    try:
        async with engine.begin() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT action, after::text FROM activity_log "
                        "WHERE action LIKE 'answer.%' AND workspace_id = :w"
                    ),
                    {"w": uuid.UUID(me.personal)},
                )
            ).all()
    finally:
        await engine.dispose()
    actions = [r[0] for r in rows]
    assert "answer.created" in actions and "answer.updated" in actions
    blob = " ".join(r[1] or "" for r in rows)
    assert marker not in blob
