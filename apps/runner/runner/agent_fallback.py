"""Constrained browser-use-style fallback for unknown forms.

Allowed actions only: fill / select / upload / click-next. Never submit.
Never leave the origin except known SSO hosts. Hard step budget.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from playwright.async_api import Page

from runner.adapters.base import Adapter
from runner.fill import click_next

SSO_HOSTS = frozenset({"accounts.google.com", "login.microsoftonline.com", "okta.com"})


async def constrained_fill(
    page: Page,
    *,
    adapter: Adapter,
    values: dict[str, str],
    step_budget: int = 20,
) -> list[dict[str, Any]]:
    """Heuristic fallback when plan-page returns mostly checkpoints/unknowns."""
    origin = urlparse(page.url).netloc
    log: list[dict[str, Any]] = []
    for step in range(step_budget):
        # Prefer labeled inputs matching known keys
        for label, key in adapter.field_map.items():
            val = values.get(key)
            if not val:
                continue
            loc = page.get_by_label(label, exact=False)
            try:
                if await loc.count():
                    await loc.first.fill(val)
                    log.append({"action": "fill", "label": label, "step": step})
            except Exception:  # noqa: S112 — try next field
                continue
            # Click next only — never submit selectors
        clicked = await click_next(page, adapter)
        log.append({"action": "click_next" if clicked else "noop", "step": step})
        if not clicked:
            break
        # Domain guard
        host = urlparse(page.url).netloc
        if host and host != origin and not any(host.endswith(s) for s in SSO_HOSTS):
            log.append({"action": "blocked_navigation", "host": host})
            break
    return log
