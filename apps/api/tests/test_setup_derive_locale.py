"""Locale deriver: currency, period, page size, radius, timezone, and neutral defaults."""

from __future__ import annotations

import pytest

from app.onboarding.derive import locale as loc


@pytest.mark.parametrize(
    ("country", "currency", "period"),
    [
        ("PH", "PHP", "month"),
        ("US", "USD", "year"),
        ("GB", "GBP", "year"),
        ("DE", "EUR", "year"),
        ("AE", "AED", "month"),
        ("AU", "AUD", "year"),
        ("SG", "SGD", "month"),
        ("IN", "INR", "month"),
        ("MY", "MYR", "month"),
        ("JP", "JPY", "year"),
        ("BR", "BRL", "year"),
        ("ZZ", "USD", "month"),
        ("", "USD", "month"),
    ],
)
def test_currency_and_period(country, currency, period):
    table = loc.locale_for(country)
    assert (table.currency, table.period) == (currency, period)


@pytest.mark.parametrize(
    ("country", "page_size"),
    [
        ("US", "letter"),
        ("CA", "letter"),
        ("PH", "letter"),
        ("MX", "letter"),
        ("CL", "letter"),
        ("GB", "a4"),
        ("DE", "a4"),
        ("ZZ", "a4"),
    ],
)
def test_page_size(country, page_size):
    assert loc.page_size_for(country) == page_size


@pytest.mark.parametrize(
    ("country", "radius"),
    [
        ("SG", 25),
        ("HK", 25),
        ("US", 80),
        ("CA", 80),
        ("AU", 80),
        ("PH", 40),
        ("DE", 40),
        ("ZZ", 40),
    ],
)
def test_radius(country, radius):
    assert loc.radius_for(country) == radius


@pytest.mark.parametrize(
    ("country", "zone"),
    [
        ("PH", "Asia/Manila"),
        ("SG", "Asia/Singapore"),
        ("GB", "Europe/London"),
        ("DE", "Europe/Berlin"),
        ("AE", "Asia/Dubai"),
        ("US", None),
        ("CA", None),
        ("AU", None),
        ("BR", None),
        ("ZZ", None),
    ],
)
def test_timezone_map_is_conservative(country, zone):
    assert loc.timezone_for(country) is None or loc.timezone_for(country) == zone
    if zone:
        assert loc.locale_for(country).timezone == zone


def test_device_timezone_is_the_fallback_for_a_multi_zone_country():
    assert loc.timezone_for("US", "America/New_York") == "America/New_York"
    assert loc.timezone_for("US", None) is None


def test_a_single_zone_country_beats_the_device():
    assert loc.timezone_for("PH", "America/New_York") == "Asia/Manila"


def test_lowercase_country_is_normalised():
    assert loc.locale_for("ph").country == "PH"
