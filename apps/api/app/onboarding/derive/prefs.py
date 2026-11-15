"""Explicit statements from a resume, with the exact quote and span.

Rules first; the AI signal step may add more, but only with a quote that exists in the text.
Eligibility is never inferred from nationality, birthplace, or where someone studied.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from app.onboarding.parse import country_from_location

_KIND_LABEL = {
    "notice": r"notice(?:\s+period)?|availability|available|start\s+date|when\s+can\s+you\s+start",
    "salary": r"expected\s+(?:salary|compensation|pay)|salary\s+expectation|desired\s+salary|"
    r"target\s+salary|salary\s+required|compensation\s+expectation|expected\s+pay",
    "relocation": r"relocation|willing\s+to\s+relocate|open\s+to\s+relocat",
    "work_authorization": r"work\s+authori[sz]ation|authori[sz]ed\s+to\s+work|right\s+to\s+work|"
    r"work\s+permit|permanent\s+resident|green\s+card|citizen|eligible\s+to\s+work",
    "sponsorship": r"sponsorship|sponsor(?:ed|ing)?|visa",
    "remote": r"remote\s+(?:only|preferred|work)|prefer\s+remote|open\s+to\s+remote|"
    r"hybrid|on[- ]?site\s+only",
}

_LABEL_LINE = re.compile(
    r"^\s*(?P<label>" + "|".join(f"(?:{v})" for v in _KIND_LABEL.values()) + r")\b"
    r"(?:\s*\([^)]{0,40}\))?\s*[:\uff1a\-\u2013\u2014]\s*(?P<value>.+)$",
    re.IGNORECASE | re.MULTILINE,
)

_NOTICE = re.compile(
    r"\b(?:available\s+immediately|immediate(?:ly)?\s+available|immediate\s+start|"
    r"(?P<num>\d{1,2})\s*(?P<unit>days?|weeks?|months?)\s*(?:of\s+)?notice|"
    r"notice\s+period\s*[:\uff1a\-\u2013\u2014]?\s*(?P<num2>\d{1,2})\s*(?P<unit2>days?|weeks?|months?)|"
    r"(?P<num3>\d{1,2})\s*(?P<unit3>days?|weeks?|months?)\s+notice)\b",
    re.IGNORECASE,
)

_AMOUNT = re.compile(
    r"(?:(?P<cur1>PHP|USD|EUR|GBP|AED|SGD|MYR|INR|AUD|CAD|HKD|JPY|CNY|IDR|THB|VND|SAR|QAR|"
    r"KWD|BHD|OMR|NZD|CHF|SEK|NOK|DKK|PLN|CZK|RON|TRY|BRL|MXN|CLP|COP|ARS|ZAR|NGN|KES|EGP|"
    r"ILS|TWD|KRW)\s*)?(?P<sym>[$\u20ac\u00a3\u20b1\u00a5])?\s*"
    r"(?P<amount>\d{1,3}(?:[,\s]\d{3})+|\d{3,9})(?:\.\d{1,2})?\s*"
    r"(?P<period>per\s+(?:month|year|annum|hour)|/\s*(?:month|year|hr|hour)|a\s+(?:month|year)|"
    r"monthly|yearly|annually|hourly)?"
)

_RELOCATION = re.compile(
    r"\b(?:willing\s+to\s+relocate|open\s+to\s+relocat(?:e|ion)|relocation\s*[:\uff1a-]\s*yes|"
    r"willing\s+to\s+move|relocating\s+to\s+[A-Za-z .'-]+)\b",
    re.IGNORECASE,
)

_AUTH = re.compile(
    r"\b(?:authori[sz]ed\s+to\s+work|legally\s+eligible\s+to\s+work|permanent\s+resident|"
    r"green\s+card\s+holder|work\s+permit|right\s+to\s+work|"
    r"(?:[A-Z][a-z]+|US|UK|UAE|EU)\s+citizen|citizen\s+of\s+[A-Z][a-z]+)\b",
    re.IGNORECASE,
)

_SPONSORSHIP = re.compile(
    r"\b(?:requires?\s+(?:visa\s+)?sponsorship|need\s+(?:visa\s+)?sponsorship|"
    r"sponsorship\s+(?:required|needed)|visa\s+required|"
    r"no\s+sponsorship\s+(?:required|needed)|do\s+not\s+require\s+sponsorship)\b",
    re.IGNORECASE,
)

_REMOTE = re.compile(
    r"\b(?:remote\s+only|prefer\s+remote|remote\s+preferred|open\s+to\s+remote|"
    r"hybrid\s+(?:only|preferred)|on[- ]?site\s+only|office\s+only)\b",
    re.IGNORECASE,
)

_CITIZEN_COUNTRY = {
    "us": "US",
    "u.s.": "US",
    "american": "US",
    "uk": "GB",
    "british": "GB",
    "filipino": "PH",
    "philippine": "PH",
    "indian": "IN",
    "malaysian": "MY",
    "singaporean": "SG",
    "australian": "AU",
    "canadian": "CA",
    "german": "DE",
    "french": "FR",
    "dutch": "NL",
    "irish": "IE",
    "spanish": "ES",
    "italian": "IT",
    "portuguese": "PT",
    "emirati": "AE",
    "saudi": "SA",
    "qatari": "QA",
    "japanese": "JP",
    "korean": "KR",
    "brazilian": "BR",
    "mexican": "MX",
    "indonesian": "ID",
    "thai": "TH",
    "vietnamese": "VN",
    "south african": "ZA",
    "nigerian": "NG",
    "kenyan": "KE",
    "egyptian": "EG",
    "israeli": "IL",
    "turkish": "TR",
    "polish": "PL",
    "czech": "CZ",
    "romanian": "RO",
    "swedish": "SE",
    "norwegian": "NO",
    "danish": "DK",
    "finnish": "FI",
    "swiss": "CH",
    "austrian": "AT",
    "belgian": "BE",
    "greek": "GR",
}

_MAX_QUOTE = 200


class SignalKind:
    NOTICE = "notice"
    SALARY = "salary"
    RELOCATION = "relocation"
    WORK_AUTHORIZATION = "work_authorization"
    SPONSORSHIP = "sponsorship"
    REMOTE = "remote"


@dataclass(frozen=True)
class Signal:
    kind: str
    value: str
    quote: str
    start: int
    end: int
    country: str | None = None
    currency: str | None = None
    period: str | None = None
    confidence: float = 0.8
    stale: bool = False


def _line_bounds(text: str, index: int) -> tuple[int, int]:
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    return start, end if end != -1 else len(text)


def _quote(text: str, start: int, end: int) -> str:
    line_start, line_end = _line_bounds(text, start)
    return text[line_start:line_end].strip()[:_MAX_QUOTE]


def _stale_date(line: str, today: date) -> bool:
    years = [int(y) for y in re.findall(r"\b(19[89]\d|20[0-4]\d)\b", line)]
    return bool(years) and max(years) <= today.year - 2


def _notice(text: str, today: date) -> Signal | None:
    match = _NOTICE.search(text)
    if match is None:
        return None
    if match.group("num") or match.group("num2") or match.group("num3"):
        number = int(match.group("num") or match.group("num2") or match.group("num3"))
        unit = (
            match.group("unit") or match.group("unit2") or match.group("unit3") or "day"
        ).rstrip("s")
        value = f"{number} {unit}{'' if number == 1 else 's'}"
    else:
        value = "Available immediately"
    line = _quote(text, match.start(), match.end())
    return Signal(
        kind=SignalKind.NOTICE,
        value=value,
        quote=line,
        start=match.start(),
        end=match.end(),
        confidence=0.9,
        stale=_stale_date(line, today),
    )


def _salary(text: str, today: date) -> Signal | None:
    for line_match in _LABEL_LINE.finditer(text):
        label = line_match.group("label").casefold()
        if not any(word in label for word in ("salary", "compensation", "pay")):
            continue
        amount = _AMOUNT.search(line_match.group("value"))
        if amount is None:
            continue
        raw = amount.group("amount").strip()
        currency = (amount.group("cur1") or "").upper()
        if not currency:
            currency = {
                "$": "USD",
                "\u20ac": "EUR",
                "\u00a3": "GBP",
                "\u20b1": "PHP",
                "\u00a5": "JPY",
            }.get(amount.group("sym") or "", "")
        period = (amount.group("period") or "").casefold()
        period_key = (
            "year"
            if "year" in period or "annum" in period or "annual" in period
            else "hour"
            if "hour" in period or "hr" in period
            else "month"
            if "month" in period
            else None
        )
        line = line_match.group(0).strip()[:_MAX_QUOTE]
        return Signal(
            kind=SignalKind.SALARY,
            value=raw,
            quote=line,
            start=line_match.start(),
            end=line_match.end(),
            currency=currency or None,
            period=period_key,
            confidence=0.8,
            stale=_stale_date(line, today),
        )
    return None


def _relocation(text: str, today: date) -> Signal | None:
    match = _RELOCATION.search(text)
    if match is None:
        return None
    line = _quote(text, match.start(), match.end())
    return Signal(
        kind=SignalKind.RELOCATION,
        value="Yes",
        quote=line,
        start=match.start(),
        end=match.end(),
        confidence=0.85,
        stale=_stale_date(line, today),
    )


def _auth(text: str, today: date, resume_country: str) -> list[Signal]:
    signals: list[Signal] = []
    match = _AUTH.search(text)
    if match is not None:
        phrase = match.group(0)
        line = _quote(text, match.start(), match.end())
        country = resume_country
        citizen = re.search(r"([A-Za-z.]+)\s+citizen|citizen\s+of\s+([A-Za-z.]+)", phrase, re.I)
        if citizen:
            word = (citizen.group(1) or citizen.group(2) or "").casefold().strip()
            country = _CITIZEN_COUNTRY.get(word) or country_from_location(word) or country
        own = country_from_location(line)
        if own:
            country = own
        signals.append(
            Signal(
                kind=SignalKind.WORK_AUTHORIZATION,
                value=phrase.strip(),
                quote=line,
                start=match.start(),
                end=match.end(),
                country=country or None,
                confidence=0.85,
                stale=_stale_date(line, today),
            )
        )
    sponsor = _SPONSORSHIP.search(text)
    if sponsor is not None:
        phrase = sponsor.group(0).casefold()
        line = _quote(text, sponsor.start(), sponsor.end())
        negative = (
            "no sponsorship" in phrase or "not require" in phrase or "do not require" in phrase
        )
        signals.append(
            Signal(
                kind=SignalKind.SPONSORSHIP,
                value="No" if negative else "Yes",
                quote=line,
                start=sponsor.start(),
                end=sponsor.end(),
                confidence=0.85,
                stale=_stale_date(line, today),
            )
        )
    return signals


def _remote(text: str, today: date) -> Signal | None:
    match = _REMOTE.search(text)
    if match is None:
        return None
    phrase = match.group(0).casefold()
    if "remote" in phrase:
        value = "Remote"
    elif "hybrid" in phrase:
        value = "Hybrid"
    else:
        value = "On-site"
    line = _quote(text, match.start(), match.end())
    return Signal(
        kind=SignalKind.REMOTE,
        value=value,
        quote=line,
        start=match.start(),
        end=match.end(),
        confidence=0.8,
        stale=_stale_date(line, today),
    )


def collect(text: str, *, resume_country: str = "", today: date | None = None) -> list[Signal]:
    """Rule signals from explicit statements only. Missing means missing, never a default."""
    today = today or date.today()
    out: list[Signal] = []
    for finder in (_notice, _salary, _relocation):
        signal = finder(text, today)
        if signal is not None:
            out.append(signal)
    out.extend(_auth(text, today, resume_country))
    remote = _remote(text, today)
    if remote is not None:
        out.append(remote)
    return out


def merge_ai(signals: list[Signal], ai_signals: Iterable[dict], text: str) -> list[Signal]:
    """Keep AI signals only when their quote exists in the text and the kind is known."""
    folded = re.sub(r"\s+", " ", text.casefold())
    kinds = {signal.kind for signal in signals}
    out = list(signals)
    for raw in ai_signals:
        kind = str(raw.get("kind") or "")
        quote = str(raw.get("quote") or "").strip()
        value = str(raw.get("value") or "").strip()
        if kind not in {
            SignalKind.NOTICE,
            SignalKind.SALARY,
            SignalKind.RELOCATION,
            SignalKind.WORK_AUTHORIZATION,
            SignalKind.SPONSORSHIP,
            SignalKind.REMOTE,
        }:
            continue
        if not quote or not value or re.sub(r"\s+", " ", quote.casefold()) not in folded:
            continue
        if kind in kinds:
            continue
        start = text.casefold().find(quote.casefold())
        out.append(
            Signal(
                kind=kind,
                value=value,
                quote=quote[:_MAX_QUOTE],
                start=max(0, start),
                end=max(0, start) + len(quote),
                country=(raw.get("country") or None),
                confidence=float(raw.get("confidence") or 0.7),
            )
        )
        kinds.add(kind)
    return out
