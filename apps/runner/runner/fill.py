"""Apply fill instructions on a Playwright page. Never clicks Submit here."""

from __future__ import annotations

from typing import Any

from playwright.async_api import Page

from runner.adapters.base import Adapter

# Accessible labels that mean "this control submits the application".
_SUBMIT_WORDS = (
    "submit",
    "send application",
    "apply now",
    "finish application",
    "complete application",
    "send my application",
)


def is_submit_like(label: str) -> bool:
    """True when a control's label/value would submit the application.

    The runner only clicks Submit inside the approved `final_review` branch, so every other
    navigation click must be screened against this list.
    """
    low = (label or "").strip().lower()
    return any(word in low for word in _SUBMIT_WORDS)


async def apply_instructions(page: Page, instructions: list[dict[str, Any]]) -> dict[str, int]:
    filled = skipped = checkpoints = 0
    for instr in instructions:
        action = instr.get("action") or "fill"
        fid = instr.get("field_id") or ""
        if action == "checkpoint":
            checkpoints += 1
            continue
        if action == "skip" or not instr.get("value"):
            skipped += 1
            continue
        loc = page.locator(f"[id={_css(fid)}], [name={_css(fid)}], [aria-label={_css(fid)}]").first
        try:
            tag = await loc.evaluate("el => el.tagName.toLowerCase()")
            if tag == "select":
                await loc.select_option(label=str(instr["value"]))
            elif (await loc.get_attribute("type")) == "file":
                # File upload handled by caller with a local path.
                skipped += 1
                continue
            else:
                await loc.fill(str(instr["value"]))
            filled += 1
        except Exception:
            skipped += 1
    return {"filled": filled, "skipped": skipped, "checkpoints": checkpoints}


def _css(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


async def _control_label(loc) -> str:
    value = (await loc.get_attribute("value")) or ""
    if value:
        return value
    try:
        return (await loc.inner_text()) or ""
    except Exception:
        return ""


async def click_first(page: Page, selectors: tuple[str, ...]) -> bool:
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            if await loc.count() and await loc.is_visible():
                await loc.click(timeout=3000)
                return True
        except Exception:  # noqa: S112 — try next selector
            continue
    return False


async def click_next(page: Page, adapter: Adapter) -> bool:
    """Click a forward-navigation control, refusing anything that would submit.

    A `next` click must never send the application. Screens the control's own label (button text
    or input value) and skips submit-like controls, then falls through to the next selector.
    """
    for sel in adapter.next_selectors:
        loc = page.locator(sel).first
        try:
            if not await loc.count() or not await loc.is_visible():
                continue
            if is_submit_like(await _control_label(loc)):
                continue
            await loc.click(timeout=3000)
            return True
        except Exception:  # noqa: S112 — try next selector
            continue
    return False
