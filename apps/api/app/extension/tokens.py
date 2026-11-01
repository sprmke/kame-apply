"""Opaque extension token helpers (never store raw tokens)."""

from __future__ import annotations

import hashlib
import secrets


def new_extension_token() -> str:
    return f"ka_ext_{secrets.token_urlsafe(32)}"


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def looks_like_extension_token(raw: str) -> bool:
    return (raw or "").startswith("ka_ext_")
