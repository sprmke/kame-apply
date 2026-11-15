"""Pure derivations for setup. No I/O, no AI, no DB: table-driven and easy to test."""

from app.onboarding.derive.locale import Locale, locale_for, timezone_for

__all__ = ["Locale", "locale_for", "timezone_for"]
