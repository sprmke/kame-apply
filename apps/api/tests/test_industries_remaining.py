"""IND-7 to IND-10: prompts, advice, detection, search plan, custom packs, extra packs."""

from __future__ import annotations

import uuid

from app.ai import prompts
from app.gaps.suggest import suggest_for_skill
from app.industries.detect import detect_industry, draft_custom_pack
from app.industries.registry import get_pack, require_pack
from app.interview.build import build_prep
from app.resumes.content import ResumeLine
from app.resumes.from_profile import build_from_profile
from app.resumes.verify import verify_line
from app.safety.rules_engine import content_rule_hits
from app.strategy.linkedin import build_suggestions
from app.tracks.plan import SearchPlanIn, plan_search
from tests.test_ai import env  # noqa: F401
from tests.test_workspaces import signup


def test_detection_and_search_plan_are_pack_aware():
    assert detect_industry("Sous chef for a hotel kitchen").pack_key == "hospitality"
    assert detect_industry("Registered nurse, ICU").pack_key == "healthcare"
    assert detect_industry("Hotel manager for a resort").pack_key == "hospitality"
    assert detect_industry("Barista for a specialty coffee bar").pack_key == "hospitality"
    assert detect_industry("Marine diesel mechanic on cruise ships").pack_key in {
        "trades",
        "general",
    }

    plan = plan_search(SearchPlanIn(text="Sous chef in a hotel kitchen"))
    assert plan.industry == "hospitality"
    assert "Sous chef" in plan.titles
    assert plan.criteria["titles"]


def test_custom_pack_draft_is_schema_valid_and_selects_building_blocks():
    draft = draft_custom_pack("marine diesel mechanic on cruise ships")
    pack = require_pack(draft["key"], custom=draft["pack"])
    assert pack.key.startswith("custom_")
    assert pack.display_name
    assert pack.role_families
    assert pack.sources.adapters
    assert pack.features.query_sources is True


def test_pack_advice_and_interview_are_pack_specific():
    hospitality = get_pack("hospitality")
    assert hospitality is not None
    suggestion, _ = suggest_for_skill("Food safety", pack=hospitality)
    assert "food safety" in suggestion.lower()

    checklist = build_suggestions(
        track_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        track_name="Sous chef",
        structured={"titles": [{"title": "Sous chef"}]},
        display_name="Ana",
        headline=None,
        summary=None,
        location="Dubai",
        experiences=[],
        skills=[],
        pack=hospitality,
    )
    assert any("Culinary Agents" in item for item in checklist.github_checklist)

    prep = build_prep(
        company="Marina Hotel",
        title="Sous chef",
        job_description="HACCP, evening shifts",
        skills=["HACCP"],
        experiences=[],
        bullets=[],
        pack=hospitality,
    )
    assert any("trial" in item["item"].lower() for item in prep["checklist"])
    assert any("stations" in question["q"].lower() for question in prep["likely_questions"])


def test_safety_flags_placement_and_visa_fees():
    hits = content_rule_hits(
        "Send the placement fee and visa fee before the interview. Pay for your uniform."
    )
    ids = {hit.rule_id for hit in hits}
    assert {"placement_fee", "visa_fee", "uniform_fee"} <= ids


def test_resume_sections_use_pack_order_and_titles():
    pack = require_pack("hospitality")
    content = build_from_profile(
        {
            "display_name": "Ana",
            "experiences": [],
            "skills": [{"id": "s1", "name": "Grill"}],
            "certifications": [
                {"id": "c1", "name": "HACCP", "issuer": "ServSafe", "expires_on": "2027-01-01"}
            ],
            "projects": [{"id": "p1", "name": "Sinigang tasting menu"}],
            "languages": [{"id": "l1", "name": "English"}],
            "facets": [
                {"id": "f1", "facet_key": "cuisine", "value": "filipino"},
                {"id": "f2", "facet_key": "station", "value": "grill"},
            ],
        },
        pack=pack,
    )
    headings = [section.heading for section in content.sections]
    assert headings[0] == "Food safety certificates"
    assert "Kitchen skills" in headings
    assert "Signature dishes and menus" in headings
    assert "Cuisines and stations" in headings
    rejected = verify_line(
        ResumeLine(text="Cuisine: 120 covers", evidence_refs=["f1"]),
        {
            "facets": [{"id": "f1", "facet_key": "cuisine", "value": "filipino"}],
            "skills": [],
            "experiences": [],
            "projects": [],
            "bullets": [],
            "education": [],
            "certifications": [],
        },
    )
    assert any(item["reason"] == "fabricated_number" for item in rejected)


def test_prompts_expose_pack_brief():
    hospitality = require_pack("hospitality")
    system = prompts.with_pack_brief(prompts.COVER_LETTER.system, hospitality)
    assert "Hospitality and food roles" in system
    assert "stations" in system.lower()


async def test_detect_draft_and_advice_endpoints(env):  # noqa: F811
    c, _ = env
    me = await signup(c)
    h = me.h(me.personal)

    detected = await c.post(
        "/api/v1/industries/detect",
        json={"text": "Sous chef for a hotel kitchen"},
        headers=h,
    )
    assert detected.status_code == 200, detected.text
    assert detected.json()["pack_key"] == "hospitality"

    draft = await c.post(
        "/api/v1/industries/draft",
        json={"description": "marine diesel mechanic on cruise ships"},
        headers=h,
    )
    assert draft.status_code == 200, draft.text
    body = draft.json()
    assert body["pack"]["key"].startswith("custom_")

    accepted = await c.post(
        "/api/v1/workspace/industries/custom",
        json={
            "key": body["key"],
            "description": "marine diesel mechanic on cruise ships",
            "base_pack": body["base_pack"],
        },
        headers=h,
    )
    assert accepted.status_code == 200, accepted.text
    experience = await c.get("/api/v1/workspace/experience", headers=h)
    assert body["key"] in experience.json()["packs"]

    profile = (await c.post("/api/v1/profiles", json={"display_name": "Ana"}, headers=h)).json()
    track = await c.post(
        "/api/v1/tracks",
        json={
            "profile_id": profile["id"],
            "name": "Diesel mechanic",
            "industry": body["key"],
            "criteria": {
                "titles": [{"title": "Diesel mechanic", "synonyms": [], "exclude": False}]
            },
        },
        headers=h,
    )
    assert track.status_code == 201, track.text
    scored = await c.post(f"/api/v1/tracks/{track.json()['id']}/score", headers=h)
    assert scored.status_code == 200, scored.text

    advice = await c.get(
        "/api/v1/sources/advice",
        params={"industry": "hospitality", "country": "AE"},
        headers=h,
    )
    assert advice.status_code == 200
    assert advice.json()["coverage"] == "partial"
    assert advice.json()["suggestions"]
