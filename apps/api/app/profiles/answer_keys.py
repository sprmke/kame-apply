"""Canonical answer-bank keys for eligibility and common form questions (PRD F1).

Country-scoped keys use a separate `country` column (ISO alpha-2), not a key suffix.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Group = Literal["eligibility", "preferences", "eeo", "sourcing", "custom"]


@dataclass(frozen=True, slots=True)
class CanonicalKey:
    key: str
    label: str
    group: Group
    country_scoped: bool = False
    default_variants: tuple[str, ...] = ()
    default_answer: str = ""
    # Suggested JSON shape for answer_json when structured data helps the apply engine.
    json_hint: str | None = None
    # Industry packs that add this key. Empty means it is available in every field.
    packs: tuple[str, ...] = ()


CANONICAL_KEYS: tuple[CanonicalKey, ...] = (
    CanonicalKey(
        "work_authorization",
        "Work authorization",
        "eligibility",
        country_scoped=True,
        default_variants=(
            "Are you authorized to work in this country?",
            "Do you have the legal right to work here?",
        ),
        json_hint="status",
    ),
    CanonicalKey(
        "sponsorship",
        "Sponsorship need",
        "eligibility",
        default_variants=(
            "Will you now or in the future require sponsorship?",
            "Do you need visa sponsorship?",
        ),
        default_answer="No",
    ),
    CanonicalKey(
        "notice_period",
        "Notice period",
        "eligibility",
        default_variants=("What is your notice period?", "When can you start?"),
    ),
    CanonicalKey(
        "salary_expectation",
        "Salary expectation",
        "preferences",
        default_variants=(
            "What are your salary expectations?",
            "Desired compensation",
        ),
        json_hint="amount,currency,period",
    ),
    CanonicalKey(
        "relocation",
        "Relocation",
        "preferences",
        default_variants=("Are you willing to relocate?", "Open to relocation?"),
    ),
    CanonicalKey(
        "remote_preference",
        "Remote preference",
        "preferences",
        default_variants=(
            "Remote, hybrid, or on-site preference?",
            "What is your preferred work arrangement?",
        ),
    ),
    CanonicalKey(
        "food_safety_certificate",
        "Food safety certificate",
        "eligibility",
        default_variants=(
            "Do you hold a food handler or food safety certificate?",
            "Food safety certification",
        ),
        json_hint="have,expires_on",
        packs=("hospitality",),
    ),
    CanonicalKey(
        "availability_days",
        "Days available",
        "preferences",
        default_variants=("Which days can you work?", "Days available"),
        json_hint="days",
        packs=("hospitality",),
    ),
    CanonicalKey(
        "shift_preference",
        "Shift preference",
        "preferences",
        default_variants=("Which shifts do you prefer?", "Shift preference"),
        json_hint="shifts",
        packs=("hospitality",),
    ),
    CanonicalKey(
        "weekend_holiday_availability",
        "Weekend and holiday availability",
        "preferences",
        default_variants=("Can you work weekends and holidays?",),
        packs=("hospitality",),
    ),
    CanonicalKey(
        "earliest_start_date",
        "Earliest start date",
        "eligibility",
        default_variants=("When can you start?", "Earliest start date"),
        packs=("hospitality",),
    ),
    CanonicalKey(
        "hourly_rate_expectation",
        "Hourly rate expectation",
        "preferences",
        default_variants=("What hourly rate are you looking for?",),
        json_hint="amount,currency,period",
        packs=("hospitality",),
    ),
    CanonicalKey(
        "reliable_transport",
        "Reliable transport",
        "eligibility",
        default_variants=("Do you have reliable transport to work?",),
        packs=("hospitality",),
    ),
    CanonicalKey(
        "accommodation_needed",
        "Accommodation needed",
        "preferences",
        default_variants=("Do you need staff accommodation?",),
        packs=("hospitality",),
    ),
    CanonicalKey(
        "knife_kit",
        "Own knife kit",
        "preferences",
        default_variants=("Do you have your own knife kit?",),
        packs=("hospitality",),
    ),
    CanonicalKey(
        "trial_shift_ok",
        "Trial shift",
        "preferences",
        default_variants=("Are you available for a trial shift?", "Stage or trial shift"),
        packs=("hospitality",),
    ),
    CanonicalKey(
        "eeo_race",
        "EEO race / ethnicity",
        "eeo",
        default_variants=("Race / ethnicity (voluntary)",),
        default_answer="Decline to self-identify",
    ),
    CanonicalKey(
        "eeo_gender",
        "EEO gender",
        "eeo",
        default_variants=("Gender (voluntary)",),
        default_answer="Decline to self-identify",
    ),
    CanonicalKey(
        "eeo_veteran",
        "EEO veteran status",
        "eeo",
        default_variants=("Veteran status (voluntary)",),
        default_answer="Decline to self-identify",
    ),
    CanonicalKey(
        "eeo_disability",
        "EEO disability",
        "eeo",
        default_variants=("Disability status (voluntary)",),
        default_answer="Decline to self-identify",
    ),
    CanonicalKey(
        "how_did_you_hear",
        "How did you hear about us",
        "sourcing",
        default_variants=(
            "How did you hear about this role?",
            "Where did you find this job?",
        ),
    ),
    CanonicalKey(
        "linkedin_url",
        "LinkedIn URL",
        "sourcing",
        default_variants=("LinkedIn profile", "LinkedIn URL"),
    ),
    CanonicalKey(
        "portfolio_url",
        "Portfolio / website",
        "sourcing",
        default_variants=("Portfolio URL", "Personal website"),
    ),
    CanonicalKey(
        "github_url",
        "GitHub URL",
        "sourcing",
        default_variants=("GitHub profile",),
    ),
)

CANONICAL_BY_KEY = {k.key: k for k in CANONICAL_KEYS}

# Common countries for quick setup of work_authorization rows.
SETUP_COUNTRIES = ("US", "CA", "GB", "AU", "SG", "PH")
