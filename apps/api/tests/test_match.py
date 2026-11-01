from datetime import date

from app.profiles.match import (
    dates_overlap,
    normalize_org,
    score_experience,
    similarity,
)


def test_normalize_org_strips_legal_suffixes():
    assert normalize_org("Acme Corp.") == normalize_org("Acme Corporation")
    assert normalize_org("St. Luke's Medical Center") == "st luke s medical center"


def test_org_containment_matches_short_vs_long_name():
    assert similarity("St. Luke's", "St. Luke's Medical Center", org=True) >= 0.88


def test_experience_match_same_employer_overlapping_dates():
    scored = score_experience(
        company_a="Acme Corp",
        title_a="Software Engineer",
        start_a=date(2019, 1, 1),
        end_a=date(2022, 1, 1),
        current_a=False,
        company_b="Acme Corporation",
        title_b="Software Engineer",
        start_b=date(2019, 1, 1),
        end_b=date(2021, 1, 1),
        current_b=False,
    )
    assert scored.is_match
    assert scored.company >= 0.88


def test_experience_non_match_different_companies():
    scored = score_experience(
        company_a="Acme",
        title_a="Engineer",
        start_a=date(2019, 1, 1),
        end_a=None,
        current_a=True,
        company_b="Beta LLC",
        title_b="Engineer",
        start_b=date(2019, 1, 1),
        end_b=None,
        current_b=True,
    )
    assert not scored.is_match


def test_dates_overlap_open_ended_current():
    assert dates_overlap(date(2020, 1, 1), None, True, date(2021, 1, 1), date(2022, 1, 1), False)
    assert not dates_overlap(
        date(2010, 1, 1), date(2012, 1, 1), False, date(2015, 1, 1), date(2016, 1, 1), False
    )


def test_title_similarity_is_case_insensitive():
    assert similarity("Registered Nurse", "registered nurse") == 1.0
