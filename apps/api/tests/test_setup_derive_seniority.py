"""Seniority deriver: title words, relevant years, overlap merging, step-up gate."""

from __future__ import annotations

from datetime import date

import pytest

from app.onboarding.derive import seniority

TODAY = date(2026, 11, 13)


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Chief Technology Officer", ["executive"]),
        ("Managing Director", ["director"]),
        ("VP of Engineering", ["director"]),
        ("Director of Operations", ["director"]),
        ("Head of Support", ["lead"]),
        ("Customer Support Supervisor", ["lead"]),
        ("Engineering Manager", ["manager"]),
        ("Principal Engineer", ["principal"]),
        ("Staff Engineer", ["staff"]),
        ("Senior Software Engineer", ["senior"]),
        ("Team Lead", ["lead"]),
        ("Associate Product Manager", ["junior"]),
        ("Graduate Developer", ["junior"]),
        ("Junior Analyst", ["junior"]),
        ("Trainee Accountant", ["intern"]),
        ("Marketing Intern", ["intern"]),
        ("Software Engineer", []),
    ],
)
def test_levels_from_title(title, expected):
    assert seniority.levels_from_title(title) == expected


@pytest.mark.parametrize(
    ("years", "expected"),
    [
        (0, "intern"),
        (0.9, "intern"),
        (1, "junior"),
        (2.9, "junior"),
        (3, "mid"),
        (5.9, "mid"),
        (6, "senior"),
        (12, "senior"),
    ],
)
def test_level_from_years(years, expected):
    assert seniority.level_from_years(years) == expected


def test_years_ignore_overlapping_roles():
    rows = [
        {"title": "Engineer", "start_date": "2020-01-01", "end_date": "2024-01-01"},
        {"title": "Engineer", "start_date": "2022-01-01", "end_date": "2024-01-01"},
    ]
    assert seniority.years_experience(rows, today=TODAY) == 4.0


def test_current_role_counts_to_today():
    rows = [{"title": "Engineer", "start_date": "2025-11-13", "is_current": True}]
    assert seniority.years_experience(rows, today=TODAY) == 1.0


def test_a_future_end_date_does_not_go_negative():
    rows = [{"title": "Engineer", "start_date": "2026-11-13", "end_date": "2024-01-01"}]
    assert seniority.years_experience(rows, today=TODAY) == 0.0


def test_relevant_years_count_only_the_same_family():
    rows = [
        {"title": "Support Lead", "start_date": "2020-01-01", "end_date": "2024-01-01"},
        {"title": "Pastry Chef", "start_date": "2015-01-01", "end_date": "2020-01-01"},
    ]
    assert seniority.relevant_years(rows, latest_title="Support Lead", today=TODAY) == 4.0


def test_no_family_match_returns_zero_not_total():
    rows = [{"title": "Pastry Chef", "start_date": "2015-01-01", "end_date": "2020-01-01"}]
    assert seniority.relevant_years(rows, latest_title="Software Engineer", today=TODAY) == 0.0


def test_title_wins_and_the_years_neighbour_is_added():
    rows = [
        {"title": "Customer Support Lead", "start_date": "2018-01-01", "end_date": "2024-01-01"},
    ]
    assert seniority.suggest_levels(
        latest_title="Customer Support Lead", experiences=rows, today=TODAY
    ) == ["lead", "senior"]


def test_years_alone_decide_when_the_title_has_no_level():
    rows = [
        {"title": "Support Specialist", "start_date": "2016-01-01", "end_date": "2024-01-01"},
    ]
    assert seniority.suggest_levels(
        latest_title="Support Specialist", experiences=rows, today=TODAY
    ) == ["senior"]


def test_intern_title_never_gets_upgraded_by_years():
    rows = [{"title": "Marketing Intern", "start_date": "2015-01-01", "end_date": "2024-01-01"}]
    assert seniority.suggest_levels(
        latest_title="Marketing Intern", experiences=rows, today=TODAY
    ) == ["intern"]


def test_step_up_needs_eighteen_months_in_the_latest_role():
    rows = [
        {"title": "Software Engineer", "start_date": "2026-01-01", "is_current": True},
        {"title": "Software Engineer", "start_date": "2016-01-01", "end_date": "2026-01-01"},
    ]
    assert (
        seniority.step_up_allowed(latest_title="Software Engineer", experiences=rows, today=TODAY)
        is False
    )


def test_step_up_allowed_with_time_and_years():
    rows = [
        {"title": "Software Engineer", "start_date": "2024-01-01", "is_current": True},
        {"title": "Software Engineer", "start_date": "2014-01-01", "end_date": "2024-01-01"},
    ]
    assert (
        seniority.step_up_allowed(latest_title="Software Engineer", experiences=rows, today=TODAY)
        is True
    )


def test_no_experience_is_no_step_up():
    assert (
        seniority.step_up_allowed(latest_title="Software Engineer", experiences=[], today=TODAY)
        is False
    )


def test_missing_dates_are_ignored():
    rows = [{"title": "Software Engineer", "start_date": None, "end_date": None}]
    assert seniority.years_experience(rows, today=TODAY) == 0.0


def test_object_rows_work_too():
    class Row:
        title = "Data Analyst"
        start_date = date(2020, 1, 1)
        end_date = date(2023, 1, 1)
        is_current = False

    assert seniority.years_experience([Row()], today=TODAY) == 3.0
