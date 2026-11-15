"""Account proposals: the caller's own name and timezone, only when still empty or UTC."""

from __future__ import annotations

from typing import Any


def account_items(
    *,
    subject: str,
    user: Any,
    device_timezone: str,
    resume_timezone: str | None,
    resume_name: str,
):
    """Return `(items, notice_keys)`. Never runs for someone the user helps."""
    from app.onboarding import schemas as s

    if subject != "self" or user is None:
        return [], ["account_skipped_other_person"] if subject != "self" else []

    items: list[s.SetupItem] = []
    if not (getattr(user, "name", None) or "").strip() and (resume_name or "").strip():
        items.append(
            s.SetupItem(
                id="account.name",
                group="account",
                target="account.name",
                kind="value",
                value=resume_name.strip()[:120],
                source="suggested",
                confidence=0.6,
                reason_key="setup.reason.account_name",
                default_on=True,
            )
        )
    if (getattr(user, "timezone", None) or "UTC") == "UTC" and device_timezone:
        items.append(
            s.SetupItem(
                id="account.timezone",
                group="account",
                target="account.timezone",
                kind="value",
                value=device_timezone,
                source="suggested",
                confidence=0.7,
                reason_key="setup.reason.device_timezone",
                reason_params={"resume": resume_timezone or ""},
                default_on=True,
            )
        )
    return items, []


def user_name_for_resume(user: Any, parsed_name: str) -> str:
    """Only fill the account name from the resume when the user row has none."""
    if (getattr(user, "name", None) or "").strip():
        return ""
    return (parsed_name or "").strip()
