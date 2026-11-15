"""Offline evals for setup: signals precision guards, grounding, and search-plan v2 guards.

No live model. The AI path is covered with a fake runner in `test_setup_ai_path.py`; these evals
guard the rules and post-processing that must hold even when a model misbehaves.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

import pytest

from app.onboarding import schemas as s
from app.onboarding.derive import prefs, searches
from app.onboarding.evidence import evidence
from app.onboarding.grounding import ground_items, quote_found

TODAY = date(2026, 11, 13)
DOC = uuid.uuid4()

RESUME = """Ana Reyes
Customer Support Lead
Manila, Philippines
Notice period: 30 days
Skills: Zendesk, SQL, onboarding
Experience
2020 - 2025 Support Lead at Acme
Cut response times by 40 percent.
"""

PLANTED = [
    "Google",
    "Stanford University",
    "Chief Technology Officer",
    "PHP 1,000,000 per month",
    "Kubernetes",
    "AWS Certified Solutions Architect",
    "10 years at Meta",
    "Fluent in Japanese",
    "Project: Mars lander",
    "Award: Employee of the Year 2024",
]


def _claim(target: str, quote: str, group: Any = "profile") -> s.SetupItem:
    return s.SetupItem(
        id=target,
        group=group,
        target=target,
        kind="value",
        value={"claim": quote},
        source="resume",
        evidence=evidence(DOC, RESUME, quote),
        reason_key="setup.reason.resume_line",
    )


def test_grounding_drops_every_planted_fact():
    kept, dropped = ground_items([_claim("profile.experience", fact) for fact in PLANTED], RESUME)
    assert kept == []
    assert dropped == len(PLANTED) == 10


def test_grounding_keeps_every_real_quote():
    kept, dropped = ground_items(
        [
            _claim("profile.headline", "Customer Support Lead"),
            _claim("profile.location", "Manila, Philippines"),
            _claim("answers.notice_period", "Notice period: 30 days", group="answers"),
        ],
        RESUME,
    )
    assert len(kept) == 3
    assert dropped == 0


def test_eligibility_never_comes_from_nationality_or_birthplace():
    cases = [
        "Nationality: Filipino",
        "Citizenship: Indian",
        "Place of birth: Cebu",
        "Born in Manila",
        "Studied in Australia",
        "Age: 34",
    ]
    for text in cases:
        signals = prefs.collect(text, resume_country="PH", today=TODAY)
        assert all(signal.kind != "work_authorization" for signal in signals), text


def test_work_authorization_needs_an_explicit_statement_and_quote():
    signals = prefs.collect("Authorized to work in the US", resume_country="PH", today=TODAY)
    auth = next(signal for signal in signals if signal.kind == "work_authorization")
    assert quote_found("Authorized to work in the US", auth.quote)
    assert auth.country == "US"


def test_ai_eligibility_without_a_quote_is_dropped():
    merged = prefs.merge_ai(
        [],
        [
            {
                "kind": "work_authorization",
                "value": "US citizen",
                "quote": "I can work anywhere",
                "country": "US",
            }
        ],
        RESUME,
    )
    assert merged == []


def test_ai_signals_cannot_add_a_kind_twice():
    rules = prefs.collect("Notice period: 30 days", today=TODAY)
    merged = prefs.merge_ai(
        rules,
        [{"kind": "notice", "value": "45 days", "quote": "Notice period: 30 days"}],
        RESUME,
    )
    assert len([signal for signal in merged if signal.kind == "notice"]) == 1


PROFILE_CONTEXTS = [
    (
        ["React", "TypeScript", "CSS"],
        "Senior Frontend Engineer",
        "Manila, Philippines",
        "PH",
        "Frontend engineer, remote",
    ),
    (["Python", "SQL", "Airflow"], "Data Engineer", "Berlin, Germany", "DE", ""),
    (["Zendesk", "SQL", "QA"], "Support Lead", "Cebu, Philippines", "PH", ""),
    (["Excel", "SAP", "Inventory"], "Warehouse Supervisor", "Kuala Lumpur, Malaysia", "MY", ""),
    (
        ["Food safety", "Menu costing"],
        "Sous Chef",
        "Dubai, United Arab Emirates",
        "AE",
        "Chef de partie",
    ),
    (["Figma", "User research"], "Product Designer", "London, United Kingdom", "GB", ""),
    (["Triage", "IV therapy"], "Registered Nurse", "Toronto, Canada", "CA", ""),
    (["Bookkeeping", "QuickBooks"], "Accountant", "Austin, United States", "US", ""),
    (["Java", "Spring"], "Backend Engineer", "Singapore", "SG", "Staff backend engineer"),
    (["Recruiting", "Sourcing"], "Talent Acquisition Partner", "Sydney, Australia", "AU", ""),
]


@pytest.mark.parametrize(
    ("profile_skills", "title", "location", "country", "role_text"),
    PROFILE_CONTEXTS,
    ids=[row[1] for row in PROFILE_CONTEXTS],
)
def test_search_plan_v2_guards_hold_on_profile_context(
    profile_skills, title, location, country, role_text
):
    inp = searches.SearchInput(
        experiences=[{"title": title, "start_date": "2020-01-01", "is_current": True}],
        headline=title,
        location=location,
        country=country,
        profile_skills=profile_skills,
        role_text=role_text,
        device_timezone="UTC",
        today=TODAY,
    )
    proposals = searches.build_all(inp)
    assert proposals
    for proposal in proposals:
        criteria = proposal.criteria
        assert set(criteria.skills.must) <= set(profile_skills)
        assert criteria.salary is None
        assert criteria.languages == []
        assert criteria.education is None
        assert criteria.clearance is None
        assert criteria.titles and all(not spec.exclude for spec in criteria.titles)
        assert len(criteria.titles) <= 5
        assert criteria.posting_max_age_days == 21
