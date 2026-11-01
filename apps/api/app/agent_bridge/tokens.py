"""Opaque OAuth token generation and hashing (never store raw tokens)."""

from __future__ import annotations

import hashlib
import secrets


def new_token(prefix: str = "ka") -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def subject_for(*, user_id, workspace_id, profile_id) -> str:
    return f"{user_id}:{workspace_id}:{profile_id}"


def parse_subject(subject: str) -> tuple[str, str, str]:
    parts = (subject or "").split(":")
    if len(parts) != 3:
        raise ValueError("invalid token subject")
    return parts[0], parts[1], parts[2]
