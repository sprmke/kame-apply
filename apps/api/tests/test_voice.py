"""Voice profile: samples, style analysis, banned phrases, audit, cross-tenant."""

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_ai import env  # noqa: F401
from tests.test_profiles import make_profile
from tests.test_workspaces import signup

P = "/api/v1/profiles"

SAMPLES = [
    {
        "text": (
            "Hey team. I shipped the night-shift handoff checklist last week. "
            "It cut missed tasks. Happy to walk through it tomorrow."
        ),
        "label": "slack",
    },
    {
        "text": (
            "Thanks for the update. I can cover Thursday evenings. "
            "Let me know if you need coverage on the weekend too."
        ),
        "label": "email",
    },
    {
        "text": (
            "I led the ICU float pool for six months. We kept ratios safe and "
            "trained three new grads. Short meetings, clear notes, no fluff."
        ),
        "label": "cover",
    },
]


async def test_voice_samples_analyze_and_banned_edit(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await make_profile(c, me)

    empty = await c.get(f"{P}/{p['id']}/voice", headers=h)
    assert empty.status_code == 200, empty.text
    body = empty.json()
    assert body["samples"] == []
    assert "seamless" in body["banned_phrases"]
    assert "passionate about" in body["banned_phrases"]

    put = await c.put(
        f"{P}/{p['id']}/voice/samples",
        json={"samples": SAMPLES},
        headers=h,
    )
    assert put.status_code == 200, put.text
    voice = put.json()
    assert len(voice["samples"]) == 3
    assert voice["analyzed_at"]
    style = voice["style"]
    assert style["sample_count"] == 3
    assert style["word_count"] > 20
    assert style["avg_sentence_length"] > 0
    assert "short" in style["summary"].lower() or "medium" in style["summary"].lower()
    assert style["vocabulary_level"] in ("plain", "mixed", "elevated")

    patched = await c.patch(
        f"{P}/{p['id']}/voice",
        json={
            "summary": "short sentences, direct, light humor, avoids jargon",
            "banned_phrases": ["leverage", "delve", "custom fluff"],
        },
        headers=h,
    )
    assert patched.status_code == 200
    assert patched.json()["style"]["summary"].startswith("short sentences")
    assert patched.json()["banned_phrases"] == ["leverage", "delve", "custom fluff"]


async def test_voice_rejects_sensitive_and_requires_samples(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await make_profile(c, me)
    bad = await c.put(
        f"{P}/{p['id']}/voice/samples",
        json={"samples": [{"text": "My SSN is 123-45-6789 and here is more padding text."}]},
        headers=h,
    )
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "sensitive_content"

    await c.get(f"{P}/{p['id']}/voice", headers=h)
    analyze = await c.post(f"{P}/{p['id']}/voice/analyze", headers=h)
    assert analyze.status_code == 422
    assert analyze.json()["error"]["code"] == "samples_required"


async def test_cross_tenant_voice_is_404(env):  # noqa: F811
    c, _ = env
    alice, mallory = await signup(c), await signup(c)
    p = await make_profile(c, alice)
    await c.put(
        f"{P}/{p['id']}/voice/samples",
        json={"samples": SAMPLES},
        headers=alice.h(alice.personal),
    )
    mh = mallory.h(mallory.personal)
    assert (await c.get(f"{P}/{p['id']}/voice", headers=mh)).status_code == 404
    assert (
        await c.put(
            f"{P}/{p['id']}/voice/samples",
            json={"samples": SAMPLES},
            headers=mh,
        )
    ).status_code == 404


async def test_rls_hides_voice_without_workspace(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    p = await make_profile(c, me)
    await c.get(f"{P}/{p['id']}/voice", headers=me.h(me.personal))
    engine = create_async_engine(TEST_DB_URL)
    try:
        async with engine.begin() as conn:
            assert (
                await conn.execute(text("SELECT count(*) FROM voice_profiles"))
            ).scalar_one() == 0
    finally:
        await engine.dispose()


async def test_audit_never_stores_sample_text(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)
    p = await make_profile(c, me)
    marker = "UNIQUE-VOICE-SAMPLE-ZZ4"
    samples = [
        {
            "text": f"{marker}. I wrote a clear note for the night team about ratios and coverage.",
            "label": "note",
        },
        {
            "text": "Second sample with enough length to pass validation for the voice analyzer.",
        },
    ]
    await c.put(f"{P}/{p['id']}/voice/samples", json={"samples": samples}, headers=h)
    engine = create_async_engine(TEST_OWNER_URL)
    try:
        async with engine.begin() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT action, after::text FROM activity_log "
                        "WHERE action LIKE 'voice.%' AND workspace_id = :w"
                    ),
                    {"w": uuid.UUID(me.personal)},
                )
            ).all()
    finally:
        await engine.dispose()
    actions = [r[0] for r in rows]
    assert "voice.created" in actions and "voice.samples_updated" in actions
    blob = " ".join(r[1] or "" for r in rows)
    assert marker not in blob


def test_style_heuristic_unit():
    from app.profiles.voice_style import analyze_samples

    style = analyze_samples(
        [
            "Hey. Short note. Done.",
            "Yeah I can cover. Let me know.",
        ]
    )
    assert style["avg_sentence_length"] < 12
    assert "short" in style["summary"]
    assert style["contraction_rate"] >= 0
