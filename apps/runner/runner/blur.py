"""Screenshot with optional PII blur boxes (label heuristics)."""

from __future__ import annotations

from pathlib import Path

from playwright.async_api import Page

_SENSITIVE = ("ssn", "social security", "national id", "passport", "bank", "card number", "dob")


async def screenshot_blurred(page: Page, path: Path) -> list[dict]:
    """Capture PNG; paint semi-opaque rects over likely-sensitive fields. Returns boxes."""
    boxes = await page.evaluate(
        """(needles) => {
      const out = [];
      for (const el of document.querySelectorAll('input, textarea')) {
        const blob = ((el.labels && el.labels[0] && el.labels[0].innerText) ||
          el.getAttribute('aria-label') || el.name || el.id || '').toLowerCase();
        if (!needles.some(n => blob.includes(n))) continue;
        const r = el.getBoundingClientRect();
        if (r.width < 2 || r.height < 2) continue;
        out.push({x: r.x, y: r.y, w: r.width, h: r.height});
      }
      return out;
    }""",
        list(_SENSITIVE),
    )
    # Overlay via DOM before screenshot, then remove.
    await page.evaluate(
        """(boxes) => {
      const root = document.createElement('div');
      root.id = 'kame-pii-blur';
      root.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:2147483647';
      for (const b of boxes) {
        const d = document.createElement('div');
        d.style.cssText = `position:fixed;left:${b.x}px;top:${b.y}px;width:${b.w}px;height:${b.h}px;background:rgba(20,20,20,0.85);backdrop-filter:blur(6px)`;
        root.appendChild(d);
      }
      document.documentElement.appendChild(root);
    }""",
        boxes,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(path), full_page=False)
    await page.evaluate("() => document.getElementById('kame-pii-blur')?.remove()")
    return boxes
