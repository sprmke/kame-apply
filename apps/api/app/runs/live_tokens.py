"""Short-lived run-scoped tokens for live-view WebSocket auth."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt

from app.core.config import Settings
from app.core.errors import AppError

ALGORITHM = "HS256"
LIVE_TYP = "live_view"
DEFAULT_TTL_SECONDS = 10 * 60


def issue_live_token(
    settings: Settings,
    *,
    run_id: uuid.UUID,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    role: Literal["viewer", "runner"],
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    exp = now + timedelta(seconds=ttl_seconds)
    claims = {
        "sub": str(user_id),
        "wid": str(workspace_id),
        "rid": str(run_id),
        "role": role,
        "typ": LIVE_TYP,
        "iat": now,
        "exp": exp,
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=ALGORITHM), exp


def decode_live_token(settings: Settings, token: str) -> dict[str, Any]:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub", "wid", "rid", "role", "typ"]},
        )
        if claims.get("typ") != LIVE_TYP:
            raise ValueError("wrong typ")
        if claims.get("role") not in {"viewer", "runner"}:
            raise ValueError("bad role")
        return {
            "user_id": uuid.UUID(claims["sub"]),
            "workspace_id": uuid.UUID(claims["wid"]),
            "run_id": uuid.UUID(claims["rid"]),
            "role": claims["role"],
        }
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise AppError("unauthenticated", "Authentication required", 401) from None
