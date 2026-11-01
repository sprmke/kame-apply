"""Platform policy constants for the browser extension."""

from __future__ import annotations

# Autofill is off by default and requires explicit terms acknowledgment.
RESTRICTED_PLATFORMS: frozenset[str] = frozenset({"linkedin", "indeed", "jobstreet", "seek"})

# Employer ATS / generic forms: autofill allowed without opt-in (still never Submit).
ATS_PLATFORMS: frozenset[str] = frozenset(
    {
        "greenhouse",
        "lever",
        "ashby",
        "workday",
        "workable",
        "smartrecruiters",
        "generic",
    }
)

ALL_PLATFORMS: frozenset[str] = RESTRICTED_PLATFORMS | ATS_PLATFORMS

PLATFORM_TERMS: dict[str, str] = {
    "linkedin": (
        "LinkedIn Easy Apply autofill stays off until you opt in. "
        "The extension fills only on your click, one step at a time, "
        "and never clicks Next or Submit. Prefer the employer ATS when available."
    ),
    "indeed": (
        "Indeed Apply autofill stays off until you opt in. "
        "The extension fills only on your click and never clicks Submit."
    ),
    "jobstreet": (
        "JobStreet Quick Apply autofill stays off until you opt in. "
        "The extension fills only on your click and never clicks Submit."
    ),
    "seek": (
        "SEEK Quick Apply autofill stays off until you opt in. "
        "The extension fills only on your click and never clicks Submit."
    ),
}


def detect_platform(url: str) -> str:
    u = (url or "").lower()
    if "linkedin.com" in u:
        return "linkedin"
    if "indeed." in u:
        return "indeed"
    if "jobstreet." in u:
        return "jobstreet"
    if "seek.com" in u or "seek.co." in u:
        return "seek"
    if "greenhouse.io" in u or "boards.greenhouse" in u:
        return "greenhouse"
    if "jobs.lever.co" in u or "lever.co" in u:
        return "lever"
    if "ashbyhq.com" in u:
        return "ashby"
    if "myworkdayjobs.com" in u or "workday.com" in u:
        return "workday"
    if "workable.com" in u:
        return "workable"
    if "smartrecruiters.com" in u:
        return "smartrecruiters"
    return "generic"
