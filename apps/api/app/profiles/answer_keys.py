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
    # Common answers offered as one-tap suggestions. The field stays free text.
    choices: tuple[str, ...] = ()
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
        choices=(
            "Yes, I am authorized",
            "Yes, with a work visa",
            "No, I need sponsorship",
        ),
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
        choices=("No", "Yes", "Not sure yet"),
    ),
    CanonicalKey(
        "notice_period",
        "Notice period",
        "eligibility",
        default_variants=("What is your notice period?", "When can you start?"),
        choices=("Immediately", "2 weeks", "30 days", "60 days", "90 days"),
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
        choices=("Open to discussion", "Market rate", "Negotiable"),
    ),
    CanonicalKey(
        "relocation",
        "Relocation",
        "preferences",
        default_variants=("Are you willing to relocate?", "Open to relocation?"),
        choices=("Yes, anywhere", "Yes, in this country", "No", "Open to discussion"),
    ),
    CanonicalKey(
        "remote_preference",
        "Remote preference",
        "preferences",
        default_variants=(
            "Remote, hybrid, or on-site preference?",
            "What is your preferred work arrangement?",
        ),
        choices=("Remote", "Hybrid", "On-site", "No preference"),
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
        choices=("Yes", "No", "Expired"),
    ),
    CanonicalKey(
        "availability_days",
        "Days available",
        "preferences",
        default_variants=("Which days can you work?", "Days available"),
        json_hint="days",
        packs=("hospitality",),
        choices=("Monday to Friday", "Weekends", "Any day"),
    ),
    CanonicalKey(
        "shift_preference",
        "Shift preference",
        "preferences",
        default_variants=("Which shifts do you prefer?", "Shift preference"),
        json_hint="shifts",
        packs=("hospitality",),
        choices=("Morning", "Afternoon", "Evening", "Night", "Rotating"),
    ),
    CanonicalKey(
        "weekend_holiday_availability",
        "Weekend and holiday availability",
        "preferences",
        default_variants=("Can you work weekends and holidays?",),
        packs=("hospitality",),
        choices=("Yes", "No", "Sometimes"),
    ),
    CanonicalKey(
        "earliest_start_date",
        "Earliest start date",
        "eligibility",
        default_variants=("When can you start?", "Earliest start date"),
        packs=("hospitality",),
        choices=("Immediately", "In 2 weeks", "In 1 month"),
    ),
    CanonicalKey(
        "hourly_rate_expectation",
        "Hourly rate expectation",
        "preferences",
        default_variants=("What hourly rate are you looking for?",),
        json_hint="amount,currency,period",
        packs=("hospitality",),
        choices=("Open to discussion", "Market rate"),
    ),
    CanonicalKey(
        "reliable_transport",
        "Reliable transport",
        "eligibility",
        default_variants=("Do you have reliable transport to work?",),
        packs=("hospitality",),
        choices=("Yes", "No"),
    ),
    CanonicalKey(
        "accommodation_needed",
        "Accommodation needed",
        "preferences",
        default_variants=("Do you need staff accommodation?",),
        packs=("hospitality",),
        choices=("No", "Yes"),
    ),
    CanonicalKey(
        "knife_kit",
        "Own knife kit",
        "preferences",
        default_variants=("Do you have your own knife kit?",),
        packs=("hospitality",),
        choices=("Yes", "No"),
    ),
    CanonicalKey(
        "trial_shift_ok",
        "Trial shift",
        "preferences",
        default_variants=("Are you available for a trial shift?", "Stage or trial shift"),
        packs=("hospitality",),
        choices=("Yes", "No"),
    ),
    CanonicalKey(
        "eeo_race",
        "EEO race / ethnicity",
        "eeo",
        default_variants=("Race / ethnicity (voluntary)",),
        default_answer="Decline to self-identify",
        choices=(
            "Decline to self-identify",
            "Asian",
            "Black or African American",
            "Hispanic or Latino",
            "White",
            "Two or more races",
        ),
    ),
    CanonicalKey(
        "eeo_gender",
        "EEO gender",
        "eeo",
        default_variants=("Gender (voluntary)",),
        default_answer="Decline to self-identify",
        choices=("Decline to self-identify", "Female", "Male", "Non-binary"),
    ),
    CanonicalKey(
        "eeo_veteran",
        "EEO veteran status",
        "eeo",
        default_variants=("Veteran status (voluntary)",),
        default_answer="Decline to self-identify",
        choices=(
            "Decline to self-identify",
            "I am not a protected veteran",
            "I am a protected veteran",
        ),
    ),
    CanonicalKey(
        "eeo_disability",
        "EEO disability",
        "eeo",
        default_variants=("Disability status (voluntary)",),
        default_answer="Decline to self-identify",
        choices=(
            "Decline to self-identify",
            "No, I do not have a disability",
            "Yes, I have a disability",
        ),
    ),
    CanonicalKey(
        "how_did_you_hear",
        "How did you hear about us",
        "sourcing",
        default_variants=(
            "How did you hear about this role?",
            "Where did you find this job?",
        ),
        choices=("Company website", "LinkedIn", "Indeed", "JobStreet", "Referral", "Other"),
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
