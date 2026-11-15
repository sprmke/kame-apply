"""Remove sensitive-class lines from resume text before extraction or any model call (P4).

Date of birth, age, gender, marital status, nationality, religion, height, weight, place of birth,
government IDs, and reference sections never reach a profile, a prompt, a log, or evidence.
Only counts and kind codes leave this module; the text itself is never logged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# `kind` -> label patterns that start a line. A colon, dash, or a value directly after the label
# is required, so ordinary prose ("managed agency budgets") never matches.
_LINE_LABELS: tuple[tuple[str, str], ...] = (
    (
        "dob",
        r"date\s+of\s+birth|birth\s*date|d\.?\s*o\.?\s*b\.?|born(?:\s+on)?|"
        r"geburtsdatum|geboren\s+am|petsa\s+ng\s+kapanganakan|tarikh\s+lahir",
    ),
    (
        "age",
        r"age|edad|umur|alter",
    ),
    (
        "gender",
        r"sex|gender|geschlecht|kasarian|jantina",
    ),
    (
        "marital_status",
        r"civil\s+status|marital\s+status|familienstand|katayuang\s+sibil|status\s+perkahwinan",
    ),
    (
        "nationality",
        r"nationality|citizenship|staatsangeh(?:ö|oe)rigkeit|nasyonalidad|warganegara|"
        r"place\s+of\s+birth|birthplace|geburtsort|lugar\s+de\s+nacimiento",
    ),
    (
        "religion",
        r"religion|religious\s+affiliation|religi(?:on|ion)|relih(i|iy)on|agama",
    ),
    (
        "height_weight",
        r"height|weight|gr(?:ö|oe)(?:ß|ss)e|gewicht|taas|timbang",
    ),
    (
        "government_id",
        r"sss(?:\s*(?:no|number|id))?|tin(?:\s*(?:no|number|id))?|philhealth|pag-?ibig|umid|"
        r"nric|aadhaar|aadhar|pan(?:\s*(?:no|number))?|passport(?:\s*(?:no|number))?|"
        r"national\s+id|emirates\s+id|iqama|saudi\s+id|residency\s+permit|"
        r"work\s+permit\s*(?:no|number)|social\s+security(?:\s*(?:no|number))?|"
        r"ausweisnummer|personalausweis",
    ),
)

_LABELS = ")|(?:".join(f"(?P<{kind}>{pattern})" for kind, pattern in _LINE_LABELS)
# A label only counts with a value: either a delimiter or digits after it. That keeps ordinary
# prose such as "Age of the team: 12 people" and "Heightened security training" in the text.
_VALUE = r"(?:[:\uff1a\-\u2013\u2014]\s*\S|\s+\d)"
_LINE_START = re.compile(
    r"^\s*(?:(?:no\.?|nr\.?|number|nomor|n[\u00fa\u00e9]mero)\s+)?(?:(?:"
    + _LABELS
    + r"))\b"
    + _VALUE,
    re.IGNORECASE,
)
_REFERENCES_HEADING = re.compile(r"^\s*(?:references?|referees?|referenzen)\b", re.IGNORECASE)


@dataclass(frozen=True)
class SensitiveLinesResult:
    text: str
    removed: int
    kinds: tuple[str, ...]


def _kind_for(line: str) -> str | None:
    match = _LINE_START.match(line)
    if not match:
        return None
    for kind, _pattern in _LINE_LABELS:
        if match.group(kind):
            return kind
    return None


def strip_sensitive_lines(text: str) -> SensitiveLinesResult:
    """Drop sensitive lines and reference sections. Idempotent and line based."""
    removed = 0
    kinds: list[str] = []
    kept: list[str] = []
    dropping_references = False

    for line in (text or "").splitlines():
        if _REFERENCES_HEADING.match(line):
            dropping_references = True
            removed += 1
            if "references" not in kinds:
                kinds.append("references")
            continue
        if dropping_references:
            # A reference block runs to the end; headings after it are rare and carry no facts
            # that setup needs.
            if line.strip():
                removed += 1
            continue
        kind = _kind_for(line)
        if kind is not None:
            removed += 1
            if kind not in kinds:
                kinds.append(kind)
            continue
        kept.append(line)

    return SensitiveLinesResult(text="\n".join(kept).strip(), removed=removed, kinds=tuple(kinds))
