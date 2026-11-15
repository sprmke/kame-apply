"""Skills deriver: years and last used from mentioning roles, strength, must/nice guards."""

from __future__ import annotations

from datetime import date

import pytest

from app.onboarding.derive import skills

TODAY = date(2026, 11, 13)


def exp(title, start, end=None, *, current=False, bullet_skills=()):
    return {
        "title": title,
        "start_date": start,
        "end_date": end,
        "is_current": current,
        "bullets": [{"text": "Worked with tools", "skills": list(bullet_skills)}],
    }


ROWS = [
    exp("Support Lead", "2020-01-01", "2024-01-01", bullet_skills=["Zendesk", "SQL"]),
    exp("Support Specialist", "2018-01-01", "2020-01-01", bullet_skills=["Zendesk"]),
    exp("QA Analyst", "2016-01-01", "2018-01-01", bullet_skills=["Testing"]),
]


def test_years_merge_overlapping_roles():
    data = skills.usage(ROWS, today=TODAY)["zendesk"]
    assert data["years"] == 6.0
    assert data["last_used"] == 2024
    assert data["roles"] == 2


def test_years_come_from_the_role_that_mentions_the_skill():
    data = skills.usage(ROWS, today=TODAY)
    assert data["sql"]["years"] == 4.0
    # A skill named only in a skills list has no role usage, so years stay empty.
    assert data.get("leadership") is None


def test_a_skill_in_no_role_has_no_usage():
    assert skills.usage(ROWS, today=TODAY).get("kubernetes") is None


def test_strength_favours_recent_and_long_use():
    zendesk = skills.strength("Zendesk", ROWS, today=TODAY)
    testing = skills.strength("Testing", ROWS, today=TODAY)
    assert zendesk > testing


def test_rank_orders_by_strength():
    ranked = skills.rank(["Testing", "Zendesk", "SQL"], ROWS)
    assert ranked[0] == "Zendesk"


def test_must_have_is_a_subset_of_the_persons_skills():
    must = skills.must_have(
        profile_skills=["Python", "SQL", "Zendesk"],
        role_skills=["Python", "Kubernetes", "SQL"],
        experiences=ROWS,
    )
    assert set(must) <= {"Python", "SQL", "Zendesk"}
    assert "Kubernetes" not in must


def test_must_have_is_empty_without_role_skills():
    assert skills.must_have(profile_skills=["Python"], role_skills=[], experiences=ROWS) == []


def test_must_have_respects_the_limit():
    own = [f"Skill {n}" for n in range(10)]
    must = skills.must_have(profile_skills=own, role_skills=own, experiences=[], limit=6)
    assert len(must) == 6


def test_nice_to_have_skips_skills_the_person_already_has():
    nice = skills.nice_to_have(
        profile_skills=["Python"],
        role_skills=["Python", "Kubernetes", "Terraform"],
        must=["Python"],
    )
    assert nice == ["Kubernetes", "Terraform"]


def test_nice_to_have_excludes_must_have():
    nice = skills.nice_to_have(
        profile_skills=[],
        role_skills=["Go", "Rust"],
        must=["Go"],
    )
    assert nice == ["Rust"]


def test_nice_to_have_is_capped():
    role = [f"Tool {n}" for n in range(20)]
    assert len(skills.nice_to_have(profile_skills=[], role_skills=role, must=[])) == 10


def test_aliases_match_js_and_javascript():
    must = skills.must_have(
        profile_skills=["JS"],
        role_skills=["JavaScript"],
        experiences=[],
    )
    assert must == ["JS"]


def test_experience_skills_are_deduped_in_order():
    rows = [
        exp("A", "2020-01-01", "2021-01-01", bullet_skills=["React", "SQL"]),
        exp("B", "2021-01-01", "2022-01-01", bullet_skills=["react", "Node"]),
    ]
    assert skills.experience_skills(rows) == ["React", "SQL", "Node"]


@pytest.mark.parametrize("rows", [[], [{"title": "X"}]])
def test_missing_dates_or_bullets_are_safe(rows):
    assert skills.usage(rows, today=TODAY) == {}
