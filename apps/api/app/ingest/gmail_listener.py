"""Optional personal/self-hosted Gmail API listener (flagged off by default).

Reading Gmail needs a restricted OAuth scope and Google verification for multi-tenant
apps. Forwarding is the default path. This module is a no-op stub unless
`GMAIL_LISTENER_ENABLED=true` and credentials are configured locally.
"""

from __future__ import annotations

import logging

from app.core.config import Settings

log = logging.getLogger(__name__)


def enabled(settings: Settings) -> bool:
    return bool(getattr(settings, "gmail_listener_enabled", False))


async def poll_once(settings: Settings) -> int:
    """Return number of new messages processed. Stub returns 0 when disabled."""
    if not enabled(settings):
        return 0
    log.warning("gmail_listener_enabled but not configured; skipping")
    return 0
