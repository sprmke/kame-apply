"""IND-5: pack weights, credentials, shifts, title groups, facet filters."""

from __future__ import annotations

from app.industries.registry import require_pack
from app.matching.hard_filters import hard_filter
from app.matching.rule_score import blend_score, rule_components
from app.tracks.criteria import CriteriaV1, TitleSpec


def _job(**overrides):
    base = {
        "title": "Assistant Head Chef",
        "normalized_title": "assistant head chef",
        "description_text": "Hotel kitchen. HACCP required. Evening shifts. Accommodation provided.",
        "locations": [],
        "facets": {
            "credentials": ["haccp"],
            "shifts": ["evening"],
            "kitchen_type": ["hotel"],
            "cuisine": ["filipino"],
            "pay_includes": ["accommodation"],
        },
    }
    base.update(overrides)
    return base


def test_hospitality_components_reward_credentials_and_shift():
    pack = require_pack("hospitality")
    criteria = CriteriaV1(
        titles=[TitleSpec(title="Sous chef")],
        shifts=["evening"],
        facets={"kitchen_type": ["hotel"]},
    )
    comps, reasons = rule_components(
        _job(), criteria, profile_credentials=["haccp", "ServSafe Manager"], pack=pack
    )
    assert comps["title"] == 90  # same title group: sous chef / assistant head chef
    assert comps["credentials"] == 100
    assert comps["shift"] == 100
    assert "Food safety credential matches" in reasons


def test_pastry_chef_is_not_sous_chef_after_pack_generic_words():
    pack = require_pack("hospitality")
    criteria = CriteriaV1(titles=[TitleSpec(title="Sous chef")])
    job = _job(title="Pastry Chef", normalized_title="pastry chef", facets={})
    comps, _ = rule_components(job, criteria, pack=pack)
    assert comps["title"] <= 35


def test_facet_filter_only_fails_when_the_posting_is_known():
    pack = require_pack("hospitality")
    criteria = CriteriaV1(titles=[TitleSpec(title="Sous chef")], facets={"kitchen_type": ["hotel"]})
    eligible, _ = hard_filter(_job(), criteria, pack=pack)
    assert eligible == "eligible"
    rejected, detail = hard_filter(_job(facets={"kitchen_type": ["bakery"]}), criteria, pack=pack)
    assert rejected == "not_eligible"
    assert "facet:kitchen_type" in detail["failed"]
    unknown, _ = hard_filter(_job(facets={}), criteria, pack=pack)
    assert unknown == "eligible"  # unknown stays neutral, never a silent rejection


def test_pack_weights_change_the_blend():
    pack = require_pack("hospitality")
    comps: dict[str, float] = {
        "title": 90.0,
        "skills": 40.0,
        "seniority": 80.0,
        "salary": 50.0,
        "freshness": 100.0,
        "location": 100.0,
        "credentials": 100.0,
        "shift": 100.0,
    }
    hosp = blend_score(comps, pack.matching.weights)
    tech = blend_score(comps, require_pack("technology").matching.weights)
    assert hosp != tech
    assert 0 <= hosp <= 100 and 0 <= tech <= 100
