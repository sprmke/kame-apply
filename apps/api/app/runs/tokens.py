"""Opaque runner tokens (never store raw)."""

from __future__ import annotations

import hashlib
import secrets


def new_runner_token() -> str:
    return f"ka_run_{secrets.token_urlsafe(32)}"


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def looks_like_runner_token(raw: str) -> bool:
    return (raw or "").startswith("ka_run_")
