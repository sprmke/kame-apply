"""Search proposals: variants, wide titles, must-have subset, and no guessed filters."""

from __future__ import annotations

from datetime import date
from typing import Any

from app.onboarding.derive import searches

TODAY = date(2026, 11, 13)


def _input(**overrides: Any) -> searches.SearchInput:
    base: dict[str, Any] = dict(
        experiences=[
            {
                "title": "Senior Frontend Engineer",
                "company": "Acme",
                "start_date": "2023-01-01",
                "is_current": True,
            },
            {
                "title": "Frontend Engineer",
                "company": "Beta",
                "start_date": "2019-01-01",
                "end_date": "2023-01-01",
                "bullets": [
                    {"text": "Built UI", "skills": ["React", "TypeScript", "CSS"]},
                ],
            },
        ],
        headline="Frontend engineer",
        location="Manila, Philippines",
        country="PH",
        profile_skills=["React", "TypeScript", "CSS", "Node"],
        role_text="",
        device_timezone="Asia/Manila",
        today=TODAY,
    )
    base.update(overrides)
    return searches.SearchInput(**base)


def test_only_the_same_role_variant_without_a_sentence():
    proposals = searches.build_all(_input())
    assert [p.variant for p in proposals] == ["same_role"]


def test_role_sentence_comes_first_and_wins():
    proposals = searches.build_all(_input(role_text="Product designer, remote"))
    assert proposals[0].variant == "you_said"
    assert proposals[0].nl_text == "Product designer, remote"


def test_the_same_role_sentence_does_not_duplicate_the_variant():
    proposals = searches.build_all(_input(role_text="Frontend engineer"))
    assert [p.variant for p in proposals] == ["you_said"]


def test_step_up_is_proposed_only_when_it_is_earned():
    proposals = searches.build_all(_input())
    assert "step_up" not in [p.variant for p in proposals]

    earned = searches.build_all(
        _input(
            experiences=[
                {
                    "title": "Frontend Engineer",
                    "start_date": "2024-01-01",
                    "is_current": True,
                    "bullets": [{"text": "UI", "skills": ["React"]}],
                },
                {
                    "title": "Frontend Engineer",
                    "start_date": "2012-01-01",
                    "end_date": "2024-01-01",
                },
            ],
            role_text="",
        )
    )
    assert "step_up" in [p.variant for p in earned]


def test_titles_always_carry_synonyms_and_never_exclusions():
    proposal = searches.build_all(_input())[0]
    titles = [spec for spec in proposal.criteria.titles if not spec.exclude]
    assert len(titles) <= 5
    assert any(spec.synonyms for spec in titles)
    assert all(not spec.exclude for spec in proposal.criteria.titles)


def test_must_have_is_a_subset_of_profile_skills():
    proposal = searches.build_all(_input())[0]
    assert set(proposal.criteria.skills.must) <= set(_input().profile_skills)


def test_nice_to_have_may_include_skills_the_person_lacks():
    proposal = searches.build_all(
        _input(role_text="Frontend engineer with React, TypeScript, Kubernetes, GraphQL")
    )[0]
    assert all(skill not in _input().profile_skills for skill in proposal.criteria.skills.nice)


def test_no_salary_languages_education_or_clearance():
    proposal = searches.build_all(_input(role_text="Frontend engineer, UX designer"))[0]
    criteria = proposal.criteria
    assert criteria.salary is None
    assert criteria.languages == []
    assert criteria.education is None
    assert criteria.clearance is None


def test_location_and_radius_follow_the_resume_country():
    proposal = searches.build_all(_input())[0]
    location = proposal.criteria.locations[0]
    assert location.place == "Manila, Philippines"
    assert location.country == "PH"
    assert location.radius_km == 40
    assert proposal.criteria.remote_eligibility.countries == ["PH"]
    assert proposal.criteria.remote_eligibility.base_tz == "Asia/Manila"


def test_remote_only_when_the_sentence_says_so():
    quiet = searches.build_all(_input())[0]
    assert quiet.criteria.work_modes == []
    remote = searches.build_all(_input(role_text="Frontend engineer, remote"))[0]
    assert remote.criteria.work_modes == ["remote"]
    assert "or remote" in remote.name


def test_seniority_reaches_the_criteria():
    proposal = searches.build_all(_input())[0]
    assert proposal.criteria.seniority


def test_no_role_signal_means_no_search():
    assert (
        searches.build_all(_input(experiences=[], headline="", role_text="", profile_skills=[]))
        == []
    )


def test_career_change_keeps_the_search_wide():
    """A chef moving to software must not get tech must-haves they cannot back up."""
    proposals = searches.build_all(
        _input(
            experiences=[{"title": "Sous Chef", "start_date": "2021-01-01", "is_current": True}],
            headline="Sous Chef",
            role_text="Junior software engineer",
            profile_skills=["Food safety", "Menu costing"],
        )
    )
    tech = proposals[0]
    assert tech.criteria.skills.must == []
    assert tech.criteria.titles[0].title
    assert tech.variant == "you_said"


def test_employment_types_come_from_history():
    contract = searches.build_all(
        _input(
            experiences=[
                {
                    "title": "Engineer",
                    "start_date": "2024-01-01",
                    "is_current": True,
                    "employment_type": "contract",
                },
                {
                    "title": "Engineer",
                    "start_date": "2023-01-01",
                    "end_date": "2024-01-01",
                    "employment_type": "freelance",
                },
                {
                    "title": "Engineer",
                    "start_date": "2022-01-01",
                    "end_date": "2023-01-01",
                    "employment_type": "full_time",
                },
            ]
        )
    )[0]
    assert contract.criteria.employment_types == [
        "contract",
        "freelance",
        "part_time",
        "full_time",
    ]


def test_schedule_defaults_match_the_cold_start():
    proposal = searches.build_all(_input())[0]
    assert proposal.schedule.preset == "every_4_hours"
    assert proposal.schedule.quiet_hours == {"start": "22:00", "end": "07:00"}
    assert proposal.schedule.daily_cap == 12
    assert proposal.schedule.timezone == "Asia/Manila"
    assert proposal.autonomy == "prepare"


def test_ai_output_cannot_widen_must_have_beyond_the_profile():
    proposals = searches.build_all(_input(role_text="Frontend engineer"))
    merged = searches.apply_model(
        proposals,
        [
            {
                "variant": "you_said",
                "titles": [{"title": "Staff Platform Engineer", "synonyms": ["SRE"]}],
                "core_skills": ["Kubernetes", "Terraform", "Go"],
                "nice_skills": ["Rust"],
                "seniority": ["staff"],
                "work_modes": ["remote"],
            }
        ],
        _input(role_text="Frontend engineer"),
    )
    criteria = merged[0].criteria
    assert set(criteria.skills.must) <= set(_input().profile_skills)
    assert criteria.salary is None
    assert criteria.languages == []
    assert criteria.work_modes == ["remote"]


def test_ai_output_with_an_unknown_variant_is_ignored():
    proposals = searches.build_all(_input())
    merged = searches.apply_model(
        proposals,
        [{"variant": "something_else", "titles": [{"title": "Chef"}]}],
        _input(),
    )
    assert merged[0].variant == proposals[0].variant
