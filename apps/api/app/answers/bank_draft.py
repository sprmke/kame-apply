"""Draft answer-bank values from profile facts (A3). Pure functions, no writes.

Rules:
- Only facts the user already entered. Eligibility claims are never guessed.
- Sensitive classes are never read or produced.
- Every draft carries where it came from; a draft the user accepts is written through the
  normal answer-bank endpoints, which audit the write.
"""

from __future__ import annotations

from typing import Any

DEFAULT_KEYS = (
    "work_authorization",
    "sponsorship",
    "salary_expectation",
    "linkedin_url",
    "github_url",
    "portfolio_url",
    "eeo_race",
    "eeo_gender",
    "eeo_veteran",
    "eeo_disability",
)

_LABELS = {
    "linkedin_url": "LinkedIn",
    "github_url": "GitHub",
    "portfolio_url": "Portfolio or website",
    "eeo_race": "Race and ethnicity (optional)",
    "eeo_gender": "Gender (optional)",
    "eeo_veteran": "Veteran status (optional)",
    "eeo_disability": "Disability status (optional)",
}
_LINK_HOSTS = {
    "linkedin_url": ("linkedin.com",),
    "github_url": ("github.com",),
    "portfolio_url": ("portfolio", "website", "notion.site", "about.me"),
}


def _money(value: Any) -> str | None:
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    if amount <= 0:
        return None
    rounded = int(amount) if amount.is_integer() else round(amount, 2)
    return f"{rounded:,}"


def _links(profile: dict[str, Any]) -> dict[str, str]:
    found: dict[str, str] = {}
    for link in profile.get("links") or []:
        if not isinstance(link, dict):
            continue
        url = str(link.get("url") or "").strip()
        label = str(link.get("label") or "").strip().casefold()
        if not url:
            continue
        lower = url.casefold()
        for key, hosts in _LINK_HOSTS.items():
            if key not in found and any(host in lower or host in label for host in hosts):
                found[key] = url
    return found


def _entry(
    key: str,
    *,
    label: str,
    question: str,
    draft: str,
    source: str,
    refs: list[str],
    note: str = "",
    country: str | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "country": country,
        "label": label,
        "question": question,
        "draft": draft,
        "source": source,
        "evidence_refs": refs,
        "message": note,
    }


def draft_bank(
    profile: dict[str, Any],
    *,
    existing: set[tuple[str, str | None]] | None = None,
    keys: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return one draft per requested key. `source` is profile, default, or needs_story."""
    wanted = tuple(keys or DEFAULT_KEYS)
    taken = existing or set()
    links = _links(profile)
    auth = profile.get("work_authorization") or {}
    prefs = profile.get("salary_prefs") or {}
    name = str(profile.get("display_name") or "").split()[0]

    out: list[dict[str, Any]] = []

    if "work_authorization" in wanted:
        countries = [str(c).upper() for c in (auth.get("countries") or []) if c]
        authorized = auth.get("authorized")
        for country in countries[:6]:
            if (("work_authorization", country)) in taken:
                continue
            if authorized is False:
                continue
            if authorized is True:
                out.append(
                    _entry(
                        "work_authorization",
                        country=country,
                        label="Work authorization",
                        question="Are you authorized to work in this country?",
                        draft="Yes",
                        source="profile",
                        refs=["profile.work_authorization"],
                        note="From the work authorization you entered.",
                    )
                )
            else:
                out.append(
                    _entry(
                        "work_authorization",
                        country=country,
                        label="Work authorization",
                        question="Are you authorized to work in this country?",
                        draft="",
                        source="needs_story",
                        refs=[],
                        note="Answer this one yourself: it is an eligibility claim.",
                    )
                )

    if "sponsorship" in wanted and ("sponsorship", None) not in taken:
        needs = auth.get("needs_sponsorship")
        if isinstance(needs, bool):
            out.append(
                _entry(
                    "sponsorship",
                    label="Sponsorship need",
                    question="Will you now or in the future require sponsorship?",
                    draft="Yes" if needs else "No",
                    source="profile",
                    refs=["profile.work_authorization"],
                    note="From the work authorization you entered.",
                )
            )

    if "salary_expectation" in wanted and ("salary_expectation", None) not in taken:
        floor = prefs.get("floor") or prefs.get("min") or prefs.get("min_monthly")
        amount = _money(floor)
        currency = str(prefs.get("currency") or "").upper()
        period = str(prefs.get("period") or "month").lower()
        if amount and currency:
            out.append(
                _entry(
                    "salary_expectation",
                    label="Salary expectation",
                    question="What are your salary expectations?",
                    draft=f"{currency} {amount} per {period}",
                    source="profile",
                    refs=["profile.salary_prefs"],
                    note="From your salary floor.",
                )
            )

    for key in ("linkedin_url", "github_url", "portfolio_url"):
        if key in wanted and (key, None) not in taken and key in links:
            out.append(
                _entry(
                    key,
                    label=_LABELS.get(key, key.replace("_", " ").title()),
                    question="Link",
                    draft=links[key],
                    source="profile",
                    refs=["profile.links"],
                    note="From a link on your profile.",
                )
            )

    for key in ("eeo_race", "eeo_gender", "eeo_veteran", "eeo_disability"):
        if key in wanted and (key, None) not in taken:
            out.append(
                _entry(
                    key,
                    label=_LABELS.get(key, key.replace("_", " ").title()),
                    question="Voluntary self-identification",
                    draft="Decline to self-identify",
                    source="default",
                    refs=[],
                    note="A safe default. Change it if you want to share.",
                )
            )

    if not out and name:
        return []
    return out
