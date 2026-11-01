"""Field-level PII classifier: public | personal | sensitive (pii-guard.mdc).

Used by the extension and runner (Phases 13/15). Unknown → sensitive (fail closed).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

PiiClass = Literal["public", "personal", "sensitive"]

# Country-aware ID / bank patterns (labels and name attrs, not values).
_SENSITIVE_LABEL = re.compile(
    r"(?i)\b(?:"
    r"ssn|social\s*security(?:\s*number)?|"
    r"sin\b|social\s*insurance|"
    r"nric|national\s*registration|"
    r"tfn|tax\s*file\s*number|"
    r"sss|philhealth|tin\b|tax\s*identification|"
    r"aadhaar|aadhar|"
    r"cpf\b|"
    r"passport|"
    r"driver.?s?\s*licen[cs]e|"
    r"national\s*id|government\s*id|"
    r"bank\s*account|routing\s*number|iban|swift|"
    r"credit\s*card|debit\s*card|cvv|cvc|"
    r"date\s*of\s*birth|dob\b|birth\s*date|"
    r"mother.?s?\s*maiden|"
    r"password|security\s*answer|pin\b|"
    r"disability|health\s*(?:condition|history)|medical|"
    r"full\s*street\s*address|home\s*address|residential\s*address"
    r")\b"
)

_SENSITIVE_NAME = re.compile(
    r"(?i)(?:^|[_-])(?:"
    r"ssn|sin|nric|tfn|aadhaar|aadhar|cpf|passport|iban|swift|cvv|cvc|"
    r"routing|account_number|bank_account|dob|date_of_birth|"
    r"password|maiden|disability|ssn_last4"
    r")(?:$|[_-])"
)

_PERSONAL_LABEL = re.compile(
    r"(?i)\b(?:"
    r"email|e-mail|phone|mobile|telephone|cell|"
    r"city|state|province|postal|zip|postcode|"
    r"gender|sex\b|race|ethnicity|veteran|eeo|"
    r"linkedin|github|portfolio|website|"
    r"salary|compensation|current\s*title|years?\s*of\s*experience"
    r")\b"
)

_PUBLIC_LABEL = re.compile(
    r"(?i)\b(?:"
    r"first\s*name|last\s*name|full\s*name|preferred\s*name|"
    r"headline|skills?|summary|cover\s*letter|"
    r"linkedin\s*url|portfolio\s*url|github\s*url"
    r")\b"
)

_AUTOCOMPLETE_SENSITIVE = {
    "cc-number",
    "cc-csc",
    "cc-exp",
    "bday",
    "bday-day",
    "bday-month",
    "bday-year",
    "current-password",
    "new-password",
}
_AUTOCOMPLETE_PERSONAL = {
    "email",
    "tel",
    "tel-national",
    "street-address",
    "address-line1",
    "address-line2",
    "postal-code",
    "country",
    "country-name",
}
_TYPE_SENSITIVE = {"password"}
_TYPE_PERSONAL = {"email", "tel"}


@dataclass(frozen=True)
class FieldClassification:
    classification: PiiClass
    reason: str
    checkpoint: bool  # True ⇒ human must type; never autofill/store


def classify_field(
    *,
    label: str | None = None,
    name: str | None = None,
    autocomplete: str | None = None,
    input_type: str | None = None,
    pattern: str | None = None,
    country: str | None = None,
) -> FieldClassification:
    """Classify a form field. Country hint can tighten ID pattern matching."""
    blob = " ".join(x for x in (label, name, autocomplete, input_type, pattern) if x)
    ac = (autocomplete or "").strip().lower()
    itype = (input_type or "").strip().lower()

    if ac in _AUTOCOMPLETE_SENSITIVE or itype in _TYPE_SENSITIVE:
        return FieldClassification("sensitive", "autocomplete_or_type", True)
    if _SENSITIVE_LABEL.search(blob) or (name and _SENSITIVE_NAME.search(name)):
        return FieldClassification("sensitive", "label_or_name", True)
    if pattern and _looks_like_id_pattern(pattern, country):
        return FieldClassification("sensitive", "pattern", True)

    if ac in _AUTOCOMPLETE_PERSONAL or itype in _TYPE_PERSONAL:
        return FieldClassification("personal", "autocomplete_or_type", False)
    if _PERSONAL_LABEL.search(blob):
        # EEO defaults are personal (stored optionally), not sensitive health details.
        return FieldClassification("personal", "label", False)

    if _PUBLIC_LABEL.search(blob):
        return FieldClassification("public", "label", False)

    # Unknown → stricter class (fail closed).
    return FieldClassification("sensitive", "unknown_default", True)


def _looks_like_id_pattern(pattern: str, country: str | None) -> bool:
    p = pattern.replace("\\\\", "\\")
    # Common national ID regex shapes in HTML pattern attrs.
    if re.search(r"\\d\{3\}[- ]?\\d\{2\}[- ]?\\d\{4\}", p):  # SSN
        return True
    if re.search(r"\\d\{3\}[- ]?\\d\{3\}[- ]?\\d\{3\}", p) and (country or "").upper() in {
        "",
        "CA",
        "CAN",
    }:
        return True
    if re.search(r"[A-Za-z]\\d\{7\}[A-Za-z]", p):  # NRIC-ish
        return True
    if re.search(r"\\d\{4\}\\s?\\d\{4\}\\s?\\d\{4\}", p):  # Aadhaar
        return True
    if re.search(r"\\d\{9,12\}", p) and (country or "").upper() in {"", "AU", "PH", "BR", "IN"}:
        return True
    return False
