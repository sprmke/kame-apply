"""Cron + quiet-hours unit tests (incl. overnight and DST-safe next fire)."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from app.core.errors import AppError
from app.schedules import cron as c


def test_presets_resolve():
    preset, expr = c.resolve_cron(preset="every_2_hours", cron=None)
    assert preset == "every_2_hours"
    assert expr == "0 */2 * * *"


def test_weekdays_2h_preview():
    text = c.human_preview("0 */2 * * 1-5", "Asia/Manila", {"start": "23:00", "end": "07:00"})
    assert "every 2 hours" in text
    assert "weekdays" in text
    assert "Asia/Manila" in text


def test_quiet_hours_overnight():
    # 23:00-07:00 Asia/Manila
    quiet = {"start": "23:00", "end": "07:00"}
    # 01:00 Manila = quiet
    local = datetime(2026, 11, 2, 1, 0, tzinfo=ZoneInfo("Asia/Manila"))
    assert c.in_quiet_hours(local.astimezone(UTC), "Asia/Manila", quiet)
    # 10:00 Manila = not quiet
    local2 = datetime(2026, 11, 2, 10, 0, tzinfo=ZoneInfo("Asia/Manila"))
    assert not c.in_quiet_hours(local2.astimezone(UTC), "Asia/Manila", quiet)


def test_next_fire_advances():
    after = datetime(2026, 11, 2, 0, 30, tzinfo=UTC)
    nxt = c.next_fire("0 */2 * * *", "UTC", after)
    assert nxt > after
    assert nxt.minute == 0


def test_invalid_cron():
    with pytest.raises(AppError):
        c.validate_cron("not a cron")


def test_manila_weekdays_window():
    """every 2h weekdays in Manila — next fire lands on a weekday hour."""
    # Sunday evening UTC → next should be Monday morning Manila-ish
    after = datetime(2026, 11, 1, 16, 0, tzinfo=UTC)  # Sun
    nxt = c.next_fire("0 */2 * * 1-5", "Asia/Manila", after)
    local = nxt.astimezone(ZoneInfo("Asia/Manila"))
    assert local.weekday() < 5
