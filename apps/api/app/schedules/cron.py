"""Cron helpers: next fire, quiet hours, human preview, presets."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter

from app.core.errors import AppError

PRESETS: dict[str, str] = {
    "hourly": "0 * * * *",
    "every_2_hours": "0 */2 * * *",
    "every_4_hours": "0 */4 * * *",
    "daily_morning": "0 8 * * *",
    "weekdays_2h": "0 */2 * * 1-5",
}


def validate_timezone(tz: str) -> str:
    try:
        ZoneInfo(tz)
    except ZoneInfoNotFoundError as exc:
        raise AppError("validation_error", f"Unknown timezone: {tz}", 422) from exc
    return tz


def validate_cron(expr: str) -> str:
    expr = expr.strip()
    parts = expr.split()
    if len(parts) != 5:
        raise AppError("validation_error", "Cron must have 5 fields (m h dom mon dow)", 422)
    try:
        croniter(expr, datetime.now(UTC))
    except (ValueError, KeyError) as exc:
        raise AppError("validation_error", f"Invalid cron: {expr}", 422) from exc
    return expr


def resolve_cron(*, preset: str | None, cron: str | None) -> tuple[str, str]:
    if preset and preset != "custom":
        if preset not in PRESETS:
            raise AppError("validation_error", f"Unknown preset: {preset}", 422)
        return preset, PRESETS[preset]
    if not cron:
        raise AppError("validation_error", "cron required for custom preset", 422)
    return "custom", validate_cron(cron)


def next_fire(cron: str, tz_name: str, after: datetime) -> datetime:
    """Next fire instant in UTC after `after`, in the schedule timezone."""
    z = ZoneInfo(tz_name)
    base = after.astimezone(z)
    itr = croniter(cron, base)
    nxt: datetime = itr.get_next(datetime)
    if nxt.tzinfo is None:
        nxt = nxt.replace(tzinfo=z)
    return nxt.astimezone(UTC)


def in_quiet_hours(now: datetime, tz_name: str, quiet: dict[str, Any] | None) -> bool:
    """Quiet hours are a local wall-clock window [start, end). Overnight windows wrap midnight."""
    if not quiet:
        return False
    start_s = quiet.get("start")
    end_s = quiet.get("end")
    if not start_s or not end_s:
        return False
    z = ZoneInfo(tz_name)
    local = now.astimezone(z)
    start = _parse_hhmm(str(start_s))
    end = _parse_hhmm(str(end_s))
    t = local.timetz().replace(tzinfo=None)
    if start <= end:
        return start <= t < end
    return t >= start or t < end


def end_of_quiet_hours(now: datetime, tz_name: str, quiet: dict[str, Any]) -> datetime:
    """UTC instant when quiet hours end after `now`."""
    z = ZoneInfo(tz_name)
    local = now.astimezone(z)
    end = _parse_hhmm(str(quiet["end"]))
    candidate = datetime.combine(local.date(), end, tzinfo=z)
    if candidate <= local:
        candidate = candidate + timedelta(days=1)
    return candidate.astimezone(UTC)


def day_start_utc(now: datetime, tz_name: str) -> datetime:
    z = ZoneInfo(tz_name)
    local = now.astimezone(z)
    start = datetime.combine(local.date(), time(0, 0), tzinfo=z)
    return start.astimezone(UTC)


def human_preview(cron: str, tz_name: str, quiet: dict[str, Any] | None = None) -> str:
    parts = cron.split()
    if len(parts) != 5:
        return cron
    minute, hour, _dom, _mon, dow = parts
    bits: list[str] = []
    if hour.startswith("*/"):
        bits.append(f"every {hour[2:]} hours")
    elif hour == "*" and minute == "0":
        bits.append("hourly")
    elif hour.isdigit() and minute.isdigit():
        bits.append(f"daily at {int(hour):02d}:{int(minute):02d}")
    else:
        bits.append(cron)
    if dow == "1-5":
        bits.append("weekdays")
    bits.append(tz_name)
    if quiet and quiet.get("start") and quiet.get("end"):
        bits.append(f"quiet {quiet['start']}-{quiet['end']}")
    return ", ".join(bits)


def _parse_hhmm(raw: str) -> time:
    try:
        h, m = raw.split(":")
        return time(int(h), int(m))
    except (ValueError, TypeError) as exc:
        raise AppError("validation_error", f"quiet hours must be HH:MM, got {raw}", 422) from exc
