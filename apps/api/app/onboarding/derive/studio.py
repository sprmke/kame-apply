"""Studio base resume proposal. Page size follows the resume country."""

from __future__ import annotations

from app.onboarding.derive.locale import page_size_for

TEMPLATE = "classic"


def base_resume(*, headline: str, country: str) -> dict[str, str]:
    label = (headline or "").strip() or "Base resume"
    return {
        "label": label[:200],
        "template": TEMPLATE,
        "page_size": page_size_for(country),
    }
