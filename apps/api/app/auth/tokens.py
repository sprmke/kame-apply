"""Access JWTs and opaque random tokens (refresh, email verify, password reset).

Opaque tokens are 256-bit random strings; only their SHA-256 is stored, so a database read
cannot be replayed as a credential. Never log either form.
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import Settings
from app.core.errors import AppError

ALGORITHM = "HS256"


def new_opaque_token() -> tuple[str, str]:
    """Return (plaintext for the client/email, sha256 hex for storage)."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def issue_access_token(settings: Settings, *, user_id: uuid.UUID, session_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),
        "sid": str(session_id),
        "typ": "access",
        "iat": now,
        "exp": now + timedelta(seconds=settings.access_token_ttl_seconds),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(settings: Settings, token: str) -> tuple[uuid.UUID, uuid.UUID]:
    """Return (user_id, session_id) or raise the same 401 for any failure."""
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub", "sid", "typ"]},
        )
        if claims["typ"] != "access":
            raise ValueError("wrong token type")
        return uuid.UUID(claims["sub"]), uuid.UUID(claims["sid"])
    except (jwt.PyJWTError, ValueError, KeyError):
        raise AppError("unauthenticated", "Authentication required", 401) from None
