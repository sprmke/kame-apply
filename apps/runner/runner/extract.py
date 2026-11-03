"""Extract form fields from a Playwright page (shared shape with extension)."""

from __future__ import annotations

from typing import Any

from playwright.async_api import Page


async def extract_fields(page: Page) -> list[dict[str, Any]]:
    return await page.evaluate(
        """() => {
      const out = [];
      const nodes = document.querySelectorAll('input, select, textarea');
      let i = 0;
      for (const el of nodes) {
        if (el.type === 'hidden' || el.disabled) continue;
        const id = el.id || el.name || `f${i++}`;
        let label = '';
        if (el.id) {
          const lab = document.querySelector(`label[for="${CSS.escape(el.id)}"]`);
          if (lab) label = lab.innerText.trim();
        }
        if (!label) {
          const parentLab = el.closest('label');
          if (parentLab) label = parentLab.innerText.trim();
        }
        if (!label) label = el.getAttribute('aria-label') || el.placeholder || el.name || '';
        const options = el.tagName === 'SELECT'
          ? Array.from(el.options).map(o => o.text.trim()).filter(Boolean)
          : [];
        out.push({
          id: String(id),
          name: el.name || '',
          label: String(label).slice(0, 200),
          type: (el.type || el.tagName.toLowerCase()),
          autocomplete: el.autocomplete || '',
          required: !!el.required,
          options,
          value: el.type === 'password' ? '' : (el.value || ''),
          section: '',
          maxlength: el.maxLength > 0 ? el.maxLength : null,
          surrounding_text: (el.closest('fieldset, section, form')?.innerText || '').slice(0, 400),
        });
      }
      return out;
    }"""
    )


async def page_text(page: Page) -> str:
    return await page.evaluate("() => document.body?.innerText?.slice(0, 8000) || ''")


def looks_like_login(text: str, needles: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(n in low for n in needles)


_CAPTCHA_SELECTORS = (
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    "iframe[src*='turnstile']",
    "div.g-recaptcha",
    "div.h-captcha",
    "#cf-turnstile",
)


async def page_has_captcha(page: Page) -> bool:
    """Only a *visible* challenge counts; a reCAPTCHA script tag alone is not a block."""
    try:
        visible = await page.evaluate(
            """(selectors) => selectors.some((sel) => {
                const el = document.querySelector(sel);
                if (!el) return false;
                const r = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return r.width > 0 && r.height > 0 && style.visibility !== 'hidden'
                  && style.display !== 'none';
            })""",
            list(_CAPTCHA_SELECTORS),
        )
    except Exception:
        visible = False
    if visible:
        return True
    text = (await page_text(page)).lower()
    return any(
        phrase in text
        for phrase in ("verify you are human", "complete the captcha", "i'm not a robot")
    )


async def page_has_password_input(page: Page) -> bool:
    try:
        return bool(
            await page.evaluate(
                """() => Array.from(document.querySelectorAll('input[type=password]')).some((el) => {
                    const r = el.getBoundingClientRect();
                    return r.width > 0 && r.height > 0 && !el.disabled;
                })"""
            )
        )
    except Exception:
        return False


def looks_like_confirmation(text: str, needles: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(n in low for n in needles)


def already_applied(text: str) -> bool:
    low = text.lower()
    return any(
        x in low for x in ("already applied", "you have already submitted", "duplicate application")
    )
