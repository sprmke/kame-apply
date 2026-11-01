"""Salary suggestion from posting range + optional market + user floor."""

from __future__ import annotations

from typing import Any

from app.strategy.schemas import SalaryAdviceRead


def _num(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def advise_salary(
    *,
    posting_salary: dict[str, Any] | None,
    user_salary_prefs: dict[str, Any] | None,
    market_p50: float | None = None,
) -> SalaryAdviceRead:
    posting = posting_salary or {}
    prefs = user_salary_prefs or {}
    currency = str(posting.get("currency") or prefs.get("currency") or "USD")
    pmin = _num(posting.get("min"))
    pmax = _num(posting.get("max"))
    floor = _num(prefs.get("floor") or prefs.get("min") or prefs.get("min_monthly"))

    suggested_min = None
    suggested_max = None
    parts: list[str] = []

    if pmin is not None and pmax is not None:
        suggested_min = pmin
        suggested_max = pmax
        parts.append(f"Posting states {pmin:g}-{pmax:g} {currency}.")
    elif pmin is not None:
        suggested_min = pmin
        suggested_max = pmin * 1.15
        parts.append(f"Posting floor {pmin:g} {currency}.")
    elif pmax is not None:
        suggested_max = pmax
        suggested_min = pmax * 0.85
        parts.append(f"Posting ceiling {pmax:g} {currency}.")
    elif market_p50 is not None:
        suggested_min = market_p50 * 0.95
        suggested_max = market_p50 * 1.05
        parts.append(f"No posting range; using market midpoint {market_p50:g}.")
    else:
        parts.append("No posting salary and no market data.")

    if floor is not None and suggested_min is not None and suggested_min < floor:
        suggested_min = floor
        parts.append(f"Raised floor to your minimum {floor:g}.")
    if floor is not None and suggested_max is not None and suggested_max < floor:
        suggested_max = floor
        parts.append("Posting is below your floor; answer carefully or skip.")

    if suggested_min is not None and suggested_max is not None and suggested_min > suggested_max:
        suggested_min, suggested_max = suggested_max, suggested_min

    return SalaryAdviceRead(
        posting_min=pmin,
        posting_max=pmax,
        posting_currency=str(posting.get("currency")) if posting.get("currency") else None,
        market_p50=market_p50,
        user_floor=floor,
        suggested_min=round(suggested_min, 2) if suggested_min is not None else None,
        suggested_max=round(suggested_max, 2) if suggested_max is not None else None,
        currency=currency,
        rationale=" ".join(parts) or "Insufficient data.",
        truthful=True,
    )
