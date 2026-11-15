"""Country → currency, pay period, page size, radius, and single-zone timezone.

The table is deliberately small and static. Unknown countries keep neutral defaults; setup never
guesses a pay figure, only the shape a person would type.
"""

from __future__ import annotations

from dataclasses import dataclass

LETTER_COUNTRIES = frozenset({"US", "CA", "PH", "MX", "CL"})
DENSE_COUNTRIES = frozenset({"SG", "HK"})
WIDE_COUNTRIES = frozenset({"US", "CA", "AU"})
DEFAULT_CURRENCY = "USD"
DEFAULT_PERIOD = "month"
DEFAULT_RADIUS_KM = 40

_CURRENCY_BY_COUNTRY: dict[str, tuple[str, str]] = {
    "AE": ("AED", "month"),
    "AR": ("ARS", "month"),
    "AT": ("EUR", "year"),
    "AU": ("AUD", "year"),
    "BE": ("EUR", "year"),
    "BH": ("BHD", "month"),
    "BR": ("BRL", "year"),
    "CA": ("CAD", "year"),
    "CH": ("CHF", "year"),
    "CL": ("CLP", "month"),
    "CN": ("CNY", "month"),
    "CO": ("COP", "month"),
    "CZ": ("CZK", "month"),
    "DE": ("EUR", "year"),
    "DK": ("DKK", "month"),
    "EG": ("EGP", "month"),
    "ES": ("EUR", "year"),
    "FI": ("EUR", "year"),
    "FR": ("EUR", "year"),
    "GB": ("GBP", "year"),
    "GR": ("EUR", "year"),
    "HK": ("HKD", "month"),
    "ID": ("IDR", "month"),
    "IE": ("EUR", "year"),
    "IL": ("ILS", "month"),
    "IN": ("INR", "month"),
    "IT": ("EUR", "year"),
    "JP": ("JPY", "year"),
    "KE": ("KES", "month"),
    "KR": ("KRW", "year"),
    "KW": ("KWD", "month"),
    "MX": ("MXN", "month"),
    "MY": ("MYR", "month"),
    "NG": ("NGN", "month"),
    "NL": ("EUR", "year"),
    "NO": ("NOK", "month"),
    "NZ": ("NZD", "year"),
    "OM": ("OMR", "month"),
    "PH": ("PHP", "month"),
    "PL": ("PLN", "month"),
    "PT": ("EUR", "year"),
    "QA": ("QAR", "month"),
    "RO": ("RON", "month"),
    "SA": ("SAR", "month"),
    "SE": ("SEK", "month"),
    "SG": ("SGD", "month"),
    "TH": ("THB", "month"),
    "TR": ("TRY", "month"),
    "TW": ("TWD", "month"),
    "US": ("USD", "year"),
    "VN": ("VND", "month"),
    "ZA": ("ZAR", "month"),
}

# Only countries with a single practical zone for resumes. Multi-zone countries get no guess.
_TIMEZONE_BY_COUNTRY: dict[str, str] = {
    "AE": "Asia/Dubai",
    "AT": "Europe/Vienna",
    "BE": "Europe/Brussels",
    "BH": "Asia/Bahrain",
    "CH": "Europe/Zurich",
    "CZ": "Europe/Prague",
    "DE": "Europe/Berlin",
    "DK": "Europe/Copenhagen",
    "EG": "Africa/Cairo",
    "ES": "Europe/Madrid",
    "FI": "Europe/Helsinki",
    "FR": "Europe/Paris",
    "GB": "Europe/London",
    "GR": "Europe/Athens",
    "HK": "Asia/Hong_Kong",
    "ID": "Asia/Jakarta",
    "IE": "Europe/Dublin",
    "IL": "Asia/Jerusalem",
    "IN": "Asia/Kolkata",
    "IT": "Europe/Rome",
    "JP": "Asia/Tokyo",
    "KE": "Africa/Nairobi",
    "KR": "Asia/Seoul",
    "KW": "Asia/Kuwait",
    "MY": "Asia/Kuala_Lumpur",
    "NG": "Africa/Lagos",
    "NL": "Europe/Amsterdam",
    "NO": "Europe/Oslo",
    "NZ": "Pacific/Auckland",
    "OM": "Asia/Muscat",
    "PH": "Asia/Manila",
    "PL": "Europe/Warsaw",
    "PT": "Europe/Lisbon",
    "QA": "Asia/Qatar",
    "RO": "Europe/Bucharest",
    "SA": "Asia/Riyadh",
    "SE": "Europe/Stockholm",
    "SG": "Asia/Singapore",
    "TH": "Asia/Bangkok",
    "TR": "Europe/Istanbul",
    "TW": "Asia/Taipei",
    "VN": "Asia/Ho_Chi_Minh",
    "ZA": "Africa/Johannesburg",
}


@dataclass(frozen=True)
class Locale:
    country: str
    currency: str
    period: str
    page_size: str
    radius_km: int
    timezone: str | None


def radius_for(country: str) -> int:
    code = (country or "").upper()
    if code in DENSE_COUNTRIES:
        return 25
    if code in WIDE_COUNTRIES:
        return 80
    return DEFAULT_RADIUS_KM


def page_size_for(country: str) -> str:
    return "letter" if (country or "").upper() in LETTER_COUNTRIES else "a4"


def locale_for(country: str) -> Locale:
    code = (country or "").upper()
    currency, period = _CURRENCY_BY_COUNTRY.get(code, (DEFAULT_CURRENCY, DEFAULT_PERIOD))
    return Locale(
        country=code,
        currency=currency,
        period=period,
        page_size=page_size_for(code),
        radius_km=radius_for(code),
        timezone=_TIMEZONE_BY_COUNTRY.get(code),
    )


def timezone_for(country: str, device_timezone: str | None = None) -> str | None:
    """A safe zone guess: the country's single zone, else the device zone, else nothing."""
    zone = _TIMEZONE_BY_COUNTRY.get((country or "").upper())
    if zone:
        return zone
    return device_timezone or None
