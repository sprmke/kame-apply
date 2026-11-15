"""Stated-preference rules: explicit statements only, with a quote, and never a guess."""

from __future__ import annotations

from datetime import date

import pytest

from app.onboarding.derive import prefs

TODAY = date(2026, 11, 13)


def _kinds(text: str, country: str = "PH") -> list[str]:
    return [signal.kind for signal in prefs.collect(text, resume_country=country, today=TODAY)]


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("Notice period: 30 days", "30 days"),
        ("2 weeks notice", "2 weeks"),
        ("1 week notice", "1 week"),
        ("3 months notice period", "3 months"),
        ("Available immediately", "Available immediately"),
    ],
)
def test_notice_formats(text, value):
    signals = prefs.collect(text, resume_country="PH", today=TODAY)
    notice = next(s for s in signals if s.kind == "notice")
    assert notice.value == value
    assert notice.quote


@pytest.mark.parametrize(
    ("text", "currency", "period"),
    [
        ("Expected salary: PHP 60,000 per month", "PHP", "month"),
        ("Salary expectation: $4,000 a month", "USD", "month"),
        ("Desired salary: EUR 70,000 per year", "EUR", "year"),
        ("Compensation expectation: £45,000 annually", "GBP", "year"),
    ],
)
def test_salary_amount_currency_period(text, currency, period):
    signals = prefs.collect(text, resume_country="PH", today=TODAY)
    salary = next(s for s in signals if s.kind == "salary")
    assert salary.currency == currency
    assert salary.period == period
    assert salary.value


def test_current_salary_is_not_an_expectation():
    assert _kinds("Current salary: 60,000 PHP a month") == []


def test_a_plain_number_is_not_a_salary_expectation():
    assert _kinds("Managed a PHP 60,000 budget") == []


def test_relocation_statement():
    signals = prefs.collect("Willing to relocate within South East Asia", today=TODAY)
    assert [(s.kind, s.value) for s in signals] == [("relocation", "Yes")]


def test_remote_statement():
    signals = prefs.collect("Remote only, please", today=TODAY)
    assert [(s.kind, s.value) for s in signals] == [("remote", "Remote")]


def test_citizenship_sets_the_country():
    signals = prefs.collect("US citizen", today=TODAY)
    auth = next(s for s in signals if s.kind == "work_authorization")
    assert auth.country == "US"


def test_permanent_resident_country_comes_from_the_line():
    signals = prefs.collect("Permanent resident, Australia", today=TODAY)
    auth = next(s for s in signals if s.kind == "work_authorization")
    assert auth.country == "AU"


def test_sponsorship_need():
    signals = prefs.collect("Requires sponsorship", today=TODAY)
    kinds = {s.kind: s.value for s in signals}
    assert kinds["sponsorship"] == "Yes"
    assert "work_authorization" not in kinds


def test_no_sponsorship_needed():
    signals = prefs.collect("No sponsorship required", today=TODAY)
    assert {s.kind: s.value for s in signals}["sponsorship"] == "No"


def test_nationality_never_implies_work_authorization():
    assert "work_authorization" not in _kinds("Nationality: Filipino")
    assert "work_authorization" not in _kinds("Citizenship: Indian")
    assert "work_authorization" not in _kinds("Born in Manila")


def test_birthplace_and_age_are_not_signals():
    assert _kinds("Date of birth: 12 May 1990\nAge: 34") == []


def test_an_old_salary_statement_is_marked_stale():
    signals = prefs.collect("Expected salary (2019): PHP 45,000 per month", today=TODAY)
    salary = next(s for s in signals if s.kind == "salary")
    assert salary.stale is True


def test_a_recent_salary_is_not_stale():
    signals = prefs.collect("Expected salary: PHP 60,000 per month", today=TODAY)
    assert next(s for s in signals if s.kind == "salary").stale is False


def test_empty_text_has_no_signals():
    assert prefs.collect("", today=TODAY) == []


def test_ai_signals_need_a_quote_in_the_text():
    signals = prefs.merge_ai(
        [],
        [
            {"kind": "notice", "value": "60 days", "quote": "60 days notice"},
            {"kind": "notice", "value": "90 days", "quote": "not in the resume"},
            {"kind": "age", "value": "34", "quote": "Age: 34"},
        ],
        "I can give 60 days notice.",
    )
    assert [(s.kind, s.value) for s in signals] == [("notice", "60 days")]


def test_ai_signals_do_not_duplicate_a_rule_signal():
    rules = prefs.collect("Notice period: 30 days", today=TODAY)
    merged = prefs.merge_ai(
        rules,
        [{"kind": "notice", "value": "45 days", "quote": "45 days notice"}],
        "Notice period: 30 days. 45 days notice.",
    )
    assert [s.value for s in merged if s.kind == "notice"] == ["30 days"]
