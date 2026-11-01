"""Backward-compatible wrappers; Phase 7 canonical path is `app.safety.sanitize`."""

from __future__ import annotations

from app.safety.sanitize import (
    SanitizeResult,
    sanitize_untrusted_html,
    sanitize_untrusted_text,
    strip_sensitive_numbers,
)

__all__ = [
    "SanitizeResult",
    "sanitize_untrusted_html",
    "sanitize_untrusted_text",
    "strip_sensitive_numbers",
]
