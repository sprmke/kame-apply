"""Profile interview: gaps, turns → proposals, accept/reject, SSE, cross-tenant."""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_ai import env  # noqa: F401
from tests.test_profiles import make_profile
from tests.test_workspaces import signup

P = "/api/v1/profiles"


async def _seed_weak_profile(c, me):
    h = me.h(me.personal)
    p = await make_profile(c, me)
    exp = (
        await c.post(
            f"{P}/{p['id']}/experiences",
            json={
                "company": "St. Luke's",
                "title": "Registered Nurse",
                "start_date": "2019-03-01",
                "end_date": "2021-06-01",
            },
            headers=h,
        )
    ).json()
    await c.post(
        f"{P}/{p['id']}/experiences",
        json={
            "company": "City Clinic",
            "title": "Charge Nurse",
            "start_date": "2022-01-01",
            "is_current": True,
        },
        headers=h,
    )
    bullet = (
        await c.post(
            f"{P}/{p['id']}/bullets",
            json={"experience_id": exp["id"], "text": "Looked after patients"},
            headers=h,
        )
    ).json()
    skill = (
        await c.post(
            f"{P}/{p['id']}/skills",
            json={"name": "Critical care"},
            headers=h,
        )
    ).json()
    return p, h, bullet, skill


async def test_gaps_turn_accept_applies_metrics(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    p, h, bullet, skill = await _seed_weak_profile(c, me)

    gaps = (await c.get(f"{P}/{p['id']}/interview/gaps", headers=h)).json()
    kinds = {g["kind"] for g in gaps}
    assert "bullet_metric" in kinds
    assert "skill_years" in kinds
    assert "gap_note" in kinds

    bullet_gap = next(g for g in gaps if g["target_id"] == bullet["id"])
    turn = await c.post(
        f"{P}/{p['id']}/interview/turns",
        json={
            "gap_id": bullet_gap["id"],
            "answer": "Managed a 12-bed ward and cut medication errors by 30%.",
        },
        headers=h,
    )
    assert turn.status_code == 201, turn.text
    proposal = turn.json()["proposal"]
    assert proposal["status"] == "pending"
    assert proposal["payload"]["metrics"]

    accepted = await c.post(
        f"{P}/{p['id']}/interview/proposals/{proposal['id']}/accept",
        headers=h,
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"

    full = (await c.get(f"{P}/{p['id']}", headers=h)).json()
    b = next(x for x in full["bullets"] if x["id"] == bullet["id"])
    assert b["source"] == "interview"
    assert b["evidence_strength"] in ("ok", "strong")
    assert b["metrics"]

    skill_gap = next(g for g in gaps if g["target_id"] == skill["id"])
    skill_turn = (
        await c.post(
            f"{P}/{p['id']}/interview/turns",
            json={"gap_id": skill_gap["id"], "answer": "About 5 years in ICU float pool."},
            headers=h,
        )
    ).json()
    await c.post(
        f"{P}/{p['id']}/interview/proposals/{skill_turn['proposal']['id']}/accept",
        headers=h,
    )
    full2 = (await c.get(f"{P}/{p['id']}", headers=h)).json()
    sk = next(x for x in full2["skills"] if x["id"] == skill["id"])
    assert float(sk["years"]) == 5.0
    assert sk["source"] == "interview"


async def test_reject_and_sse_stream(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    p, h, bullet, _ = await _seed_weak_profile(c, me)
    gaps = (await c.get(f"{P}/{p['id']}/interview/gaps", headers=h)).json()
    gap = next(g for g in gaps if g["target_id"] == bullet["id"])
    turn = (
        await c.post(
            f"{P}/{p['id']}/interview/turns",
            json={"gap_id": gap["id"], "answer": "Trained 3 new grads."},
            headers=h,
        )
    ).json()
    rejected = await c.post(
        f"{P}/{p['id']}/interview/proposals/{turn['proposal']['id']}/reject",
        headers=h,
    )
    assert rejected.json()["status"] == "rejected"
    full = (await c.get(f"{P}/{p['id']}", headers=h)).json()
    b = next(x for x in full["bullets"] if x["id"] == bullet["id"])
    assert b["source"] == "user"

    stream = await c.get(f"{P}/{p['id']}/interview/stream", headers=h)
    assert stream.status_code == 200
    assert "text/event-stream" in stream.headers["content-type"]
    body = stream.text
    assert "event: gap" in body and "event: token" in body and "event: done" in body


async def test_cross_tenant_interview_404(env):  # noqa: F811
    c, _ = env
    alice, mallory = await signup(c), await signup(c)
    p, h, bullet, _ = await _seed_weak_profile(c, alice)
    gaps = (await c.get(f"{P}/{p['id']}/interview/gaps", headers=h)).json()
    gap = next(g for g in gaps if g["target_id"] == bullet["id"])
    prop = (
        await c.post(
            f"{P}/{p['id']}/interview/turns",
            json={"gap_id": gap["id"], "answer": "Cut wait times by 20%."},
            headers=h,
        )
    ).json()["proposal"]
    mh = mallory.h(mallory.personal)
    assert (await c.get(f"{P}/{p['id']}/interview/gaps", headers=mh)).status_code == 404
    assert (
        await c.post(
            f"{P}/{p['id']}/interview/proposals/{prop['id']}/accept",
            headers=mh,
        )
    ).status_code == 404


async def test_rls_and_audit_hide_answer_text(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    p, h, bullet, _ = await _seed_weak_profile(c, me)
    marker = "UNIQUE-INTERVIEW-ANSWER-YY2"
    gaps = (await c.get(f"{P}/{p['id']}/interview/gaps", headers=h)).json()
    gap = next(g for g in gaps if g["target_id"] == bullet["id"])
    await c.post(
        f"{P}/{p['id']}/interview/turns",
        json={"gap_id": gap["id"], "answer": f"{marker} managed 8 beds."},
        headers=h,
    )
    engine = create_async_engine(TEST_DB_URL)
    try:
        async with engine.begin() as conn:
            assert (
                await conn.execute(text("SELECT count(*) FROM profile_proposals"))
            ).scalar_one() == 0
    finally:
        await engine.dispose()

    engine = create_async_engine(TEST_OWNER_URL)
    try:
        async with engine.begin() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT action, after::text FROM activity_log "
                        "WHERE action LIKE 'interview.%' AND workspace_id = :w"
                    ),
                    {"w": uuid.UUID(me.personal)},
                )
            ).all()
    finally:
        await engine.dispose()
    assert any(r[0] == "interview.proposal_created" for r in rows)
    blob = " ".join(r[1] or "" for r in rows)
    assert marker not in blob
