"""Rule-based resume text reading. No AI, no network, no storage.

Used by `POST /onboarding/plan` so setup never blocks on an AI key (PRD P7). The
output is a draft: the user checks every field before it becomes a profile fact.
Sensitive classes (government IDs, cards, dates of birth, street addresses) are
never returned. Only name, email, headline, location, skills, and years.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

MAX_TEXT = 20_000
_ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d\ufeff\u2060]")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_YEAR = re.compile(r"\b(19[89]\d|20[0-4]\d)\b")
_PLACE = re.compile(
    r"^[A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+)*,\s*[A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+)*$"
)
_NAME = re.compile(r"^[A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,3}$")
_ALLCAPS_NAME = re.compile(r"^[A-Z][A-Z.'-]+(?:\s+[A-Z][A-Z.'-]+){1,3}$")
_ROLE_WORDS = re.compile(
    r"(engineer|developer|designer|manager|lead|specialist|analyst|assistant|support|"
    r"nurse|teacher|accountant|coordinator|director|consultant|technician|supervisor|"
    r"administrator|officer|scientist|architect|writer|editor|marketer|recruiter|chef|"
    r"server|barista|driver|clerk|agent|representative|associate|head of)",
    re.I,
)
_SKIP_LINE = re.compile(r"^(resume|curriculum vitae|cv|profile|contact|summary)\b", re.I)

# Country names that appear in resume headers. Used only to prefill a country picker;
# the value is never saved as a fact and never becomes an eligibility claim.
_COUNTRY_BY_NAME: dict[str, str] = {
    "philippines": "PH",
    "united states": "US",
    "united states of america": "US",
    "usa": "US",
    "u.s.a.": "US",
    "united kingdom": "GB",
    "great britain": "GB",
    "england": "GB",
    "scotland": "GB",
    "wales": "GB",
    "northern ireland": "GB",
    "canada": "CA",
    "australia": "AU",
    "new zealand": "NZ",
    "singapore": "SG",
    "malaysia": "MY",
    "indonesia": "ID",
    "thailand": "TH",
    "vietnam": "VN",
    "viet nam": "VN",
    "japan": "JP",
    "south korea": "KR",
    "korea": "KR",
    "taiwan": "TW",
    "hong kong": "HK",
    "china": "CN",
    "india": "IN",
    "pakistan": "PK",
    "bangladesh": "BD",
    "sri lanka": "LK",
    "nepal": "NP",
    "united arab emirates": "AE",
    "uae": "AE",
    "dubai": "AE",
    "abu dhabi": "AE",
    "saudi arabia": "SA",
    "qatar": "QA",
    "kuwait": "KW",
    "bahrain": "BH",
    "oman": "OM",
    "israel": "IL",
    "turkey": "TR",
    "egypt": "EG",
    "south africa": "ZA",
    "nigeria": "NG",
    "kenya": "KE",
    "ghana": "GH",
    "morocco": "MA",
    "germany": "DE",
    "france": "FR",
    "netherlands": "NL",
    "the netherlands": "NL",
    "belgium": "BE",
    "ireland": "IE",
    "spain": "ES",
    "portugal": "PT",
    "italy": "IT",
    "switzerland": "CH",
    "austria": "AT",
    "poland": "PL",
    "czech republic": "CZ",
    "czechia": "CZ",
    "slovakia": "SK",
    "hungary": "HU",
    "romania": "RO",
    "bulgaria": "BG",
    "greece": "GR",
    "sweden": "SE",
    "norway": "NO",
    "denmark": "DK",
    "finland": "FI",
    "iceland": "IS",
    "estonia": "EE",
    "latvia": "LV",
    "lithuania": "LT",
    "ukraine": "UA",
    "russia": "RU",
    "brazil": "BR",
    "mexico": "MX",
    "chile": "CL",
    "colombia": "CO",
    "argentina": "AR",
    "peru": "PE",
    "uruguay": "UY",
}
_COUNTRY_CODES = frozenset(_COUNTRY_BY_NAME.values())
_COUNTRY_CODE_TAIL = re.compile(r"(?:^|[,\s])([A-Z]{2})$")
_URL = re.compile(r"https?://[^\s<>()\[\]{}\"']+", re.IGNORECASE)
_BARE_PROFILE_URL = re.compile(
    r"\b((?:www\.)?(?:linkedin\.com|github\.com)/[^\s<>()\[\]{}\"']+)", re.IGNORECASE
)


def clean_text(text: str) -> str:
    """Strip control and zero-width characters and cap the length. Never logs the text."""
    out = _ZERO_WIDTH.sub("", text or "")
    out = "".join(ch for ch in out if ch == "\n" or ch == "\t" or ord(ch) >= 32)
    return out[:MAX_TEXT]


def _lines(text: str) -> list[str]:
    return [line.strip(" \t-*•|") for line in text.splitlines() if line.strip()]


def _year_span(lines: list[str]) -> int | None:
    years = [int(y) for y in _YEAR.findall("\n".join(lines))]
    years = [y for y in years if 1980 <= y <= datetime.now().year]
    if not years:
        return None
    span = datetime.now().year - min(years)
    return max(1, min(50, span)) if span >= 1 else None


def country_from_location(location: str) -> str:
    """A ISO alpha-2 hint from a resume location line. Empty when unsure.

    This only prefills a picker. It is never stored as a profile fact and never used as an
    eligibility claim (work authorization stays an explicit statement).
    """
    text = (location or "").strip()
    if not text:
        return ""
    folded = text.casefold().replace(".", "").replace(",", " ")
    words = " ".join(folded.split())
    for name, code in sorted(_COUNTRY_BY_NAME.items(), key=lambda item: -len(item[0])):
        key = name.replace(".", "")
        if words == key or words.endswith(f" {key}"):
            return code
    tail = _COUNTRY_CODE_TAIL.search(text.upper())
    if tail and tail.group(1) in _COUNTRY_CODES:
        return tail.group(1)
    return ""


def looks_like_resume(text: str) -> bool:
    """A weak, explainable test: enough text, a year, and at least one role word.

    A false negative is a notice and a "Use it anyway" choice, never a silent rejection.
    """
    body = clean_text(text or "")
    if len(body.strip()) < 200:
        return False
    has_year = bool(re.search(r"\b(?:19[89]\d|20[0-4]\d)\b", body))
    return has_year and bool(_ROLE_WORDS.search(body))


_LANGUAGE_MARKERS: dict[str, tuple[str, ...]] = {
    "es": (
        "experiencia",
        "educación",
        "educacion",
        "habilidades",
        "conocimientos",
        "formación",
        "formacion",
        "idiomas",
    ),
    "de": (
        "berufserfahrung",
        "ausbildung",
        "kenntnisse",
        "lebenslauf",
        "sprachen",
        "beruflicher werdegang",
    ),
    "fr": (
        "expérience professionnelle",
        "expérience",
        "formation",
        "compétences",
        "langues",
        "parcours",
    ),
    "pt": ("experiência", "experiencia", "formação", "competências", "habilidades", "idiomas"),
}


def detect_language(text: str) -> str:
    """Pick a resume's main language from heading words. English is the fallback."""
    folded = (text or "").casefold()
    scores = {
        code: sum(1 for word in words if word in folded)
        for code, words in _LANGUAGE_MARKERS.items()
    }
    best = max(scores, key=lambda code: scores[code])
    return best if scores[best] >= 2 else "en"


def _links(text: str) -> list[dict[str, str]]:
    """https links only. They are stored as text and never fetched (P5, SSRF)."""
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    candidates = _URL.findall(text) + [f"https://{m}" for m in _BARE_PROFILE_URL.findall(text)]
    for raw in candidates:
        url = raw.rstrip(".,;:)]}")
        lowered = url.lower()
        if not lowered.startswith("https://") or len(url) > 500:
            continue
        key = lowered.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        if "linkedin.com/" in lowered:
            label = "LinkedIn"
        elif "github.com/" in lowered:
            label = "GitHub"
        else:
            label = "Portfolio"
        out.append({"label": label, "url": url})
        if len(out) >= 30:
            break
    return out


def parse_resume_text(text: str) -> dict[str, Any]:
    """Extract a conservative draft. Missing fields stay missing, never guessed."""
    body = clean_text(text)
    lines = _lines(body)[:120]
    email = (_EMAIL.search(body) or [""])[0] if _EMAIL.search(body) else ""

    head = lines[:18]
    name = ""
    for line in head:
        if _EMAIL.search(line) or _PLACE.match(line) or _SKIP_LINE.match(line):
            continue
        if len(line) <= 48 and (_NAME.match(line) or _ALLCAPS_NAME.match(line)):
            name = line
            break

    headline = ""
    for line in head:
        if line == name or _EMAIL.search(line) or _PLACE.match(line):
            continue
        if len(line) <= 90 and _ROLE_WORDS.search(line) and not _SKIP_LINE.match(line):
            headline = line
            break

    location = ""
    for line in head:
        if _PLACE.match(line) and len(line) <= 80:
            location = line
            break

    skills: list[str] = []
    for i, line in enumerate(lines):
        if re.match(r"^skills?\b", line, re.I):
            raw = re.sub(r"^skills?\s*:?\s*", "", line, flags=re.I)
            if not raw and i + 1 < len(lines):
                raw = lines[i + 1] or ""
            parts = [p.strip() for p in re.split(r"[,;|•/]", raw)]
            skills = [p for p in parts if 1 < len(p) <= 40][:15]
            break

    return {
        "name": name,
        "email": email,
        "headline": headline,
        "location": location,
        "country": country_from_location(location),
        "links": _links(body),
        "skills": skills,
        "years": _year_span(lines),
    }
