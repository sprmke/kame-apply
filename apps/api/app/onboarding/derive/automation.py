"""Automation defaults for a new search. Same values as the A8 recommendation for a cold start."""

from __future__ import annotations

from typing import Any

PRESET = "every_4_hours"
QUIET_HOURS = {"start": "22:00", "end": "07:00"}
DAILY_CAP = 12
AUTONOMY = "prepare"


def schedule_defaults(*, timezone: str) -> dict[str, Any]:
    return {
        "preset": PRESET,
        "timezone": timezone or "UTC",
        "quiet_hours": dict(QUIET_HOURS),
        "daily_cap": DAILY_CAP,
    }
