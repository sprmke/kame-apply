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


def looks_like_captcha(page_html: str) -> bool:
    low = page_html.lower()
    return any(
        x in low
        for x in ("recaptcha", "hcaptcha", "cf-turnstile", "captcha", "verify you are human")
    )


def looks_like_confirmation(text: str, needles: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(n in low for n in needles)


def already_applied(text: str) -> bool:
    low = text.lower()
    return any(
        x in low for x in ("already applied", "you have already submitted", "duplicate application")
    )
