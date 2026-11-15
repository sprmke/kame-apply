"""Titles deriver: employer noise, specialty words, synonyms, and the total cap."""

from __future__ import annotations

import pytest

from app.onboarding.derive import titles


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Engineer II, Payments Platform", "Engineer"),
        ("Software Engineer III", "Software Engineer"),
        ("Senior Frontend Engineer at Acme", "Senior Frontend Engineer"),
        ("Pastry Chef", "Pastry Chef"),
        ("ICU Nurse", "ICU Nurse"),
        ("Nurse, ICU", "Nurse (ICU)"),
        ("Accountant - Finance Team", "Accountant"),
        ("  Data   Analyst  ", "Data Analyst"),
        ("", ""),
        ("Customer Support Lead | Acme", "Customer Support Lead"),
    ],
)
def test_clean_title(raw, expected):
    assert titles.clean_title(raw) == expected


def test_synonyms_from_family_words():
    assert "developer" in titles.synonyms_for("Software Engineer")
    assert "customer service" in titles.synonyms_for("Customer Support Lead")
    assert "staff nurse" in titles.synonyms_for("Registered Nurse")


def test_generic_title_gets_a_variant_not_an_empty_list():
    variants = titles.synonyms_for("Logistics Coordinator")
    assert variants  # keeps a hard title filter from excluding common posting names


def test_headline_is_a_title_only_when_it_names_a_role():
    assert titles.headline_title("Frontend engineer") == "Frontend engineer"
    assert titles.headline_title("Building calm software for busy teams") == ""


def test_role_titles_take_the_latest_two_plus_the_headline():
    experiences = [
        {"title": "Staff Engineer, Payments"},
        {"title": "Senior Engineer at Beta"},
        {"title": "Engineer at Gamma"},
    ]
    primary, synonyms = titles.role_titles(experiences=experiences, headline="Platform engineer")
    assert primary == ["Staff Engineer", "Senior Engineer", "Platform engineer"]
    assert synonyms
    assert all(synonym.casefold() not in {p.casefold() for p in primary} for synonym in synonyms)


def test_role_titles_are_capped_at_five():
    primary, _ = titles.role_titles(
        experiences=[{"title": f"Engineer {n}"} for n in range(8)],
        headline="Engineer",
    )
    assert len(primary) <= 5


def test_duplicate_titles_are_removed():
    primary, _ = titles.role_titles(
        experiences=[{"title": "Software Engineer"}, {"title": "software engineer"}],
        headline="Software Engineer",
    )
    assert primary == ["Software Engineer"]


def test_step_up_titles():
    assert titles.step_up_title("Software Engineer") == "Senior Software Engineer"
    assert titles.step_up_title("Senior Software Engineer") == "Lead Software Engineer"
    assert titles.step_up_title("Lead Engineer") == "Principal Engineer"


def test_no_experience_and_no_headline_is_empty():
    primary, synonyms = titles.role_titles(experiences=[], headline="")
    assert primary == []
    assert synonyms == []
