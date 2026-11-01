"""In-process sliding-window rate limiter.

Single API instance on the free tier, so memory is enough (no Redis, PRD P7). If the API ever
runs more than one instance, move this to Postgres or accept the per-instance multiplier.
"""

from __future__ import annotations

import ipaddress
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.errors import AppError


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, *, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and now - hits[0] > window_seconds:
            hits.popleft()
        if len(hits) >= limit:
            raise AppError(
                "rate_limited",
                "Too many attempts. Try again later.",
                429,
                {"retry_after_seconds": int(window_seconds - (now - hits[0])) + 1},
            )
        hits.append(now)
        if len(self._hits) > 10_000:  # bound memory under a key-spraying attack
            for k in [k for k, v in self._hits.items() if not v or now - v[-1] > window_seconds]:
                del self._hits[k]

    def reset(self) -> None:
        self._hits.clear()


def _peer_in_trusted(peer: str, networks: list[str]) -> bool:
    if not networks:
        return False
    try:
        addr = ipaddress.ip_address(peer)
    except ValueError:
        return False
    for raw in networks:
        try:
            if "/" in raw:
                if addr in ipaddress.ip_network(raw, strict=False):
                    return True
            elif addr == ipaddress.ip_address(raw):
                return True
        except ValueError:
            continue
    return False


def client_ip(request: Request) -> str:
    """Client address for rate limits. Trust X-Forwarded-* only from configured proxies."""
    peer = request.client.host if request.client else "unknown"
    settings = getattr(getattr(request, "app", None), "state", None)
    networks: list[str] = []
    if settings is not None and getattr(settings, "settings", None) is not None:
        networks = settings.settings.trusted_proxy_networks
    if not _peer_in_trusted(peer, networks):
        return peer
    real = (request.headers.get("x-real-ip") or "").strip()
    if real:
        return real
    xff = (request.headers.get("x-forwarded-for") or "").strip()
    if xff:
        return xff.split(",")[0].strip()
    return peer
