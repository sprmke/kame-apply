"""Merge preview + resolve for a second resume against an existing profile."""

from __future__ import annotations

import io
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.ai.service import StructuredAiResult
from app.core.config import Settings
from app.core.mail import Outbox
from app.main import create_app
from app.profiles.parse_schema import ProfileExtract
from tests.conftest import TEST_DB_URL, TEST_OWNER_URL
from tests.test_profiles import make_profile
from tests.test_workspaces import signup

P = "/api/v1/profiles"

SECOND_DRAFT = {
    "display_name": {"value": "Ana Reyes", "confidence": 0.9},
    "headline": {"value": "Senior Registered Nurse", "confidence": 0.85},
    "summary": {"value": None, "confidence": 0.1},
    "location": {"value": "Quezon City", "confidence": 0.8},
    "timezone": {"value": None, "confidence": 0.1},
    "language": {"value": "en", "confidence": 0.7},
    "links": [],
    "experiences": [
        {
            "company": "St. Luke's Medical Center",
            "title": "Registered Nurse",
            "start_date": "2019-03-01",
            "end_date": "2021-12-01",
            "is_current": False,
            "description": "ICU",
            "confidence": 0.9,
            "bullets": [
                {
                    "text": "Managed a 12-bed ward",
                    "metrics": [],
                    "skills": [],
                    "confidence": 0.8,
                },
                {
                    "text": "Mentored six new graduate nurses",
                    "metrics": [{"name": "mentees", "value": 6}],
                    "skills": [],
                    "confidence": 0.85,
                },
            ],
        },
        {
            "company": "City Clinic",
            "title": "Staff Nurse",
            "start_date": "2017-01-01",
            "end_date": "2019-02-01",
            "is_current": False,
            "confidence": 0.88,
            "bullets": [{"text": "Triage and admissions", "confidence": 0.8}],
        },
    ],
    "projects": [],
    "education": [
        {
            "institution": "UP Manila",
            "degree": "BSN",
            "field": "Nursing",
            "confidence": 0.9,
        }
    ],
    "certifications": [],
    "languages": [{"name": "English", "proficiency": "native", "confidence": 0.8}],
    "skills": [{"name": "Patient care", "level": "expert", "confidence": 0.8}],
}


@pytest.fixture
async def env_merge():
    settings = Settings(
        database_url=TEST_DB_URL,
        environment="test",
        log_json=False,
        auth_rate_limit_enabled=False,
    )
    app = create_app(settings)
    app.state.mailer = Outbox()

    async def fake_runner(ctx, settings, **kwargs):
        return StructuredAiResult(
            ProfileExtract.model_validate(SECOND_DRAFT),
            "gemini",
            "fake-model",
            10,
            20,
            0,
        )

    app.state.run_structured = fake_runner
    async with app.router.lifespan_context(app):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t"
        ) as c:
            yield c, app


async def _seed_profile(c, me) -> dict:
    """First resume already applied via section CRUD (empty → confirm path not needed)."""
    h = me.h(me.personal)
    p = await make_profile(c, me, display_name="Ana Reyes", headline="Registered Nurse")
    exp = (
        await c.post(
            f"{P}/{p['id']}/experiences",
            json={
                "company": "St. Luke's",
                "title": "Registered Nurse",
                "start_date": "2019-03-01",
                "is_current": True,
                "description": "Night shifts",
            },
            headers=h,
        )
    ).json()
    await c.post(
        f"{P}/{p['id']}/bullets",
        json={"experience_id": exp["id"], "text": "Managed a 12-bed ward"},
        headers=h,
    )
    await c.post(
        f"{P}/{p['id']}/education",
        json={"institution": "UP Manila", "degree": "BSN"},
        headers=h,
    )
    await c.post(
        f"{P}/{p['id']}/languages",
        json={"name": "English", "proficiency": "fluent"},
        headers=h,
    )
    await c.post(f"{P}/{p['id']}/skills", json={"name": "Patient care"}, headers=h)
    return p


async def _upload_and_parse(c, me, profile_id: str) -> dict:
    h = me.h(me.personal)
    doc = (
        await c.post(
            f"{P}/{profile_id}/documents",
            files={"file": ("v2.txt", io.BytesIO(b"Ana Reyes older resume\n"), "text/plain")},
            headers=h,
        )
    ).json()
    r = await c.post(f"{P}/{profile_id}/documents/{doc['id']}/parse", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


async def test_confirm_requires_merge_when_profile_has_facts(env_merge):
    c, _ = env_merge
    me = await signup(c)
    p = await _seed_profile(c, me)
    doc = await _upload_and_parse(c, me, p["id"])
    r = await c.post(
        f"{P}/{p['id']}/documents/{doc['id']}/confirm",
        json={},
        headers=me.h(me.personal),
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "merge_required"


async def test_merge_preview_shows_date_conflict_addition_and_match(env_merge):
    c, _ = env_merge
    me = await signup(c)
    p = await _seed_profile(c, me)
    doc = await _upload_and_parse(c, me, p["id"])
    prev = await c.get(
        f"{P}/{p['id']}/documents/{doc['id']}/merge",
        headers=me.h(me.personal),
    )
    assert prev.status_code == 200, prev.text
    body = prev.json()
    assert body["summary"]["additions"] >= 1  # City Clinic
    assert any(a["label"].startswith("City Clinic") for a in body["additions"])
    # St. Luke's should conflict on dates / is_current (existing current vs ended 2021).
    exp_conflicts = [x for x in body["conflicts"] if x["section"] == "experiences"]
    assert exp_conflicts
    fields = exp_conflicts[0]["fields"]
    assert "end_date" in fields or "is_current" in fields
    assert any(
        b["text"].startswith("Mentored six")
        for x in (body["conflicts"] + body["matches"])
        for b in x.get("bullet_additions", [])
    )
    # Headline differs (conflict); blank location is an auto-fill, not a conflict.
    header_fields = {h["field"] for h in body["header_conflicts"]}
    assert "headline" in header_fields
    assert body["auto_header"].get("location") == "Quezon City"


async def test_merge_resolve_take_incoming_dates_and_add_new_job(env_merge):
    c, _ = env_merge
    me = await signup(c)
    h = me.h(me.personal)
    p = await _seed_profile(c, me)
    doc = await _upload_and_parse(c, me, p["id"])
    prev = (await c.get(f"{P}/{p['id']}/documents/{doc['id']}/merge", headers=h)).json()

    resolutions = [
        {
            "id": c["id"],
            "action": "merge",
            "field_actions": {f: "take_incoming" for f in c["fields"]},
        }
        for c in prev["conflicts"]
    ]
    header = [{"field": hc["field"], "action": "take_incoming"} for hc in prev["header_conflicts"]]
    additions = [{"id": a["id"], "action": "add"} for a in prev["additions"]]

    r = await c.post(
        f"{P}/{p['id']}/documents/{doc['id']}/merge",
        json={"resolutions": resolutions, "header": header, "additions": additions},
        headers=h,
    )
    assert r.status_code == 200, r.text
    stats = r.json()["stats"]
    assert stats["created"] >= 1
    assert stats["bullets_added"] >= 1

    full = (await c.get(f"{P}/{p['id']}", headers=h)).json()
    assert full["headline"] == "Senior Registered Nurse"
    assert full["location"] == "Quezon City"
    companies = {e["company"] for e in full["experiences"]}
    assert any("Luke" in co for co in companies)
    assert any("City Clinic" in co for co in companies)
    luke = next(e for e in full["experiences"] if "Luke" in e["company"])
    assert luke["is_current"] is False
    assert luke["end_date"] == "2021-12-01"
    bullet_texts = {b["text"] for b in full["bullets"]}
    assert "Mentored six new graduate nurses" in bullet_texts
    # Language proficiency taken from incoming when conflicted.
    assert full["languages"][0]["proficiency"] == "native"

    # Document marked confirmed; second merge rejected.
    again = await c.post(
        f"{P}/{p['id']}/documents/{doc['id']}/merge",
        json={"resolutions": [], "header": [], "additions": []},
        headers=h,
    )
    assert again.status_code == 409


async def test_merge_unresolved_conflict_rejected(env_merge):
    c, _ = env_merge
    me = await signup(c)
    h = me.h(me.personal)
    p = await _seed_profile(c, me)
    doc = await _upload_and_parse(c, me, p["id"])
    prev = (await c.get(f"{P}/{p['id']}/documents/{doc['id']}/merge", headers=h)).json()
    assert prev["conflicts"] or prev["header_conflicts"]
    r = await c.post(
        f"{P}/{p['id']}/documents/{doc['id']}/merge",
        json={"resolutions": [], "header": [], "additions": []},
        headers=h,
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "unresolved_conflicts"


async def test_merge_skip_addition_and_keep_existing(env_merge):
    c, _ = env_merge
    me = await signup(c)
    h = me.h(me.personal)
    p = await _seed_profile(c, me)
    doc = await _upload_and_parse(c, me, p["id"])
    prev = (await c.get(f"{P}/{p['id']}/documents/{doc['id']}/merge", headers=h)).json()
    resolutions = [{"id": c["id"], "action": "keep_existing"} for c in prev["conflicts"]]
    header = [{"field": hc["field"], "action": "keep_existing"} for hc in prev["header_conflicts"]]
    additions = [{"id": a["id"], "action": "skip"} for a in prev["additions"]]
    # Skip new bullets too.
    bullet_actions = [
        {"id": b["id"], "action": "skip"}
        for item in prev["conflicts"] + prev["matches"]
        for b in item.get("bullet_additions", [])
    ]
    r = await c.post(
        f"{P}/{p['id']}/documents/{doc['id']}/merge",
        json={
            "resolutions": resolutions,
            "header": header,
            "additions": additions,
            "bullet_actions": bullet_actions,
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    full = (await c.get(f"{P}/{p['id']}", headers=h)).json()
    assert full["headline"] == "Registered Nurse"
    assert len(full["experiences"]) == 1
    assert full["experiences"][0]["is_current"] is True
    assert {b["text"] for b in full["bullets"]} == {"Managed a 12-bed ward"}


async def test_cross_tenant_merge_is_404(env_merge):
    c, _ = env_merge
    alice, mallory = await signup(c), await signup(c)
    p = await _seed_profile(c, alice)
    doc = await _upload_and_parse(c, alice, p["id"])
    mh = mallory.h(mallory.personal)
    assert (
        await c.get(f"{P}/{p['id']}/documents/{doc['id']}/merge", headers=mh)
    ).status_code == 404
    mine = await make_profile(c, mallory)
    assert (
        await c.post(
            f"{P}/{mine['id']}/documents/{doc['id']}/merge",
            json={"resolutions": [], "header": [], "additions": []},
            headers=mh,
        )
    ).status_code == 404


async def test_merge_audit_has_no_resume_text(env_merge):
    c, _ = env_merge
    me = await signup(c)
    h = me.h(me.personal)
    p = await _seed_profile(c, me)
    doc = await _upload_and_parse(c, me, p["id"])
    prev = (await c.get(f"{P}/{p['id']}/documents/{doc['id']}/merge", headers=h)).json()
    resolutions = [{"id": c["id"], "action": "take_incoming"} for c in prev["conflicts"]]
    header = [{"field": hc["field"], "action": "keep_existing"} for hc in prev["header_conflicts"]]
    additions = [{"id": a["id"], "action": "skip"} for a in prev["additions"]]
    await c.post(
        f"{P}/{p['id']}/documents/{doc['id']}/merge",
        json={"resolutions": resolutions, "header": header, "additions": additions},
        headers=h,
    )
    engine = create_async_engine(TEST_OWNER_URL)
    try:
        async with engine.begin() as conn:
            rows = (
                await conn.execute(
                    text(
                        "SELECT action, after::text FROM activity_log "
                        "WHERE action='document.merged' AND workspace_id=:w"
                    ),
                    {"w": uuid.UUID(me.personal)},
                )
            ).all()
    finally:
        await engine.dispose()
    assert rows
    blob = " ".join(r[1] or "" for r in rows)
    assert "Mentored six" not in blob and "Quezon" not in blob
