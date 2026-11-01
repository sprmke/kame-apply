"""Salary period + FX normalization. ECB reference rates (or bundled fallback).

When a rate is missing, keep the original salary and set `rate_missing` so filters
skip USD comparison and the UI can show a note.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from app.tracks.criteria import CriteriaV1, SalaryFilter

# Approximate ECB-style USD cross rates for offline/tests. Refresh script replaces these.
# Values are "units of currency per 1 USD" inverted to "USD per 1 unit" as floats.
FALLBACK_USD_PER_UNIT: dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "CAD": 0.74,
    "AUD": 0.66,
    "SGD": 0.76,
    "JPY": 0.0067,
    "CHF": 1.12,
    "INR": 0.012,
    "PHP": 0.017,
    "AED": 0.27,
    "SAR": 0.27,
    "NZD": 0.60,
    "HKD": 0.13,
    "MYR": 0.23,
    "ZAR": 0.055,
}

PERIOD_TO_MONTHLY = {
    "hour": 160.0,  # ~40h/week
    "day": 20.0,  # ~20 workdays
    "month": 1.0,
    "year": 1.0 / 12.0,
}


def usd_per_unit(currency: str, rates: dict[str, float] | None = None) -> float | None:
    table = rates or FALLBACK_USD_PER_UNIT
    return table.get(currency.upper())


def to_monthly(amount: float, period: str) -> float:
    factor = PERIOD_TO_MONTHLY.get(period)
    if factor is None:
        raise ValueError(f"unknown period {period}")
    return amount * factor


def normalize_salary_filter(
    salary: SalaryFilter, rates: dict[str, float] | None = None
) -> SalaryFilter:
    rate = usd_per_unit(salary.currency, rates)
    data = salary.model_dump()
    if rate is None:
        data["rate_missing"] = True
        data["min_monthly_usd"] = None
        data["max_monthly_usd"] = None
        return SalaryFilter.model_validate(data)
    data["rate_missing"] = False
    if salary.min is not None:
        data["min_monthly_usd"] = round(to_monthly(salary.min, salary.period) * rate, 2)
    if salary.max is not None:
        data["max_monthly_usd"] = round(to_monthly(salary.max, salary.period) * rate, 2)
    return SalaryFilter.model_validate(data)


def normalize_salary(criteria: CriteriaV1, rates: dict[str, float] | None = None) -> CriteriaV1:
    if criteria.salary is None:
        return criteria
    data = criteria.model_dump(mode="json")
    data["salary"] = normalize_salary_filter(criteria.salary, rates).model_dump(mode="json")
    return CriteriaV1.model_validate(data)


def rates_payload(as_of: date | None = None) -> dict[str, Any]:
    """Shape stored in currency_rates table / cache."""
    return {
        "as_of": (as_of or date.today()).isoformat(),
        "base": "USD",
        "rates": dict(FALLBACK_USD_PER_UNIT),
        "source": "fallback",
    }
