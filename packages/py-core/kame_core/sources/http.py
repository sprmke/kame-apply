"""Polite HTTP client for source adapters (no evasion)."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

DEFAULT_UA = "KameApplyBot/0.1 (+https://kame.apply/bot; polite job discovery)"


class BlockSignalError(Exception):
    """Source returned a block/challenge; caller must disable and alert, never retry via evasion."""

    def __init__(self, status: int, host: str, detail: str = ""):
        self.status = status
        self.host = host
        self.detail = detail
        super().__init__(f"block_signal status={status} host={host} {detail}".strip())


@dataclass
class CircuitBreaker:
    failure_threshold: int = 5
    cooldown_seconds: float = 300.0
    failures: int = 0
    opened_at: float | None = None

    def allow(self) -> bool:
        if self.opened_at is None:
            return True
        if time.monotonic() - self.opened_at >= self.cooldown_seconds:
            self.opened_at = None
            self.failures = 0
            return True
        return False

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self, *, block: bool = False) -> None:
        self.failures += 1
        if block or self.failures >= self.failure_threshold:
            self.opened_at = time.monotonic()


@dataclass
class HostLimiter:
    """In-process per-host concurrency + rate limit (DBOS queue mirrors this in production)."""

    concurrency: int = 1
    per_minute: int = 30
    _sems: dict[str, asyncio.Semaphore] = field(default_factory=dict)
    _hits: dict[str, list[float]] = field(default_factory=dict)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def _sem(self, host: str) -> asyncio.Semaphore:
        if host not in self._sems:
            self._sems[host] = asyncio.Semaphore(self.concurrency)
        return self._sems[host]

    async def acquire(self, host: str) -> None:
        await self._sem(host).acquire()
        async with self._lock:
            now = time.monotonic()
            window = self._hits.setdefault(host, [])
            cutoff = now - 60.0
            self._hits[host] = [t for t in window if t > cutoff]
            if len(self._hits[host]) >= self.per_minute:
                sleep_for = 60.0 - (now - self._hits[host][0]) + 0.05
                await asyncio.sleep(max(sleep_for, 0.05))
            self._hits.setdefault(host, []).append(time.monotonic())

    def release(self, host: str) -> None:
        self._sem(host).release()


_global_limiter = HostLimiter()
_breakers: dict[str, CircuitBreaker] = {}


def breaker_for(host: str) -> CircuitBreaker:
    if host not in _breakers:
        _breakers[host] = CircuitBreaker()
    return _breakers[host]


def reset_politeness_state() -> None:
    """Test helper."""
    _breakers.clear()
    _global_limiter._hits.clear()


def _is_block(status: int, body: str) -> bool:
    if status in (429, 403, 999):
        return True
    low = body[:2000].lower()
    markers = ("captcha", "cf-challenge", "attention required", "access denied", "bot detection")
    return status == 503 and any(m in low for m in markers)


async def fetch_json(
    url: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    json_body: Any = None,
    etag: str | None = None,
    last_modified: str | None = None,
    request_timeout: float = 45.0,
    client: httpx.AsyncClient | None = None,
    user_agent: str = DEFAULT_UA,
    max_retries: int = 3,
) -> tuple[Any | None, dict[str, str], int]:
    """Return (parsed_json_or_None_if_304, response_headers, status)."""
    host = httpx.URL(url).host or "unknown"
    br = breaker_for(host)
    if not br.allow():
        raise BlockSignalError(0, host, "circuit_open")

    hdrs = {"User-Agent": user_agent, "Accept": "application/json, text/xml, */*"}
    if headers:
        hdrs.update(headers)
    if etag:
        hdrs["If-None-Match"] = etag
    if last_modified:
        hdrs["If-Modified-Since"] = last_modified

    owns = client is None
    client = client or httpx.AsyncClient(follow_redirects=True, timeout=request_timeout)
    try:
        last_exc: Exception | None = None
        for attempt in range(max_retries):
            await _global_limiter.acquire(host)
            try:
                resp = await client.request(method, url, headers=hdrs, json=json_body)
                text = resp.text
                if _is_block(resp.status_code, text):
                    br.record_failure(block=True)
                    raise BlockSignalError(resp.status_code, host, text[:200])
                if resp.status_code == 304:
                    br.record_success()
                    return None, dict(resp.headers), 304
                if resp.status_code >= 500:
                    br.record_failure()
                    last_exc = httpx.HTTPStatusError(
                        f"server {resp.status_code}", request=resp.request, response=resp
                    )
                    # Jitter for polite backoff (not crypto).
                    await asyncio.sleep((2**attempt) + random.random())  # noqa: S311
                    continue
                if resp.status_code >= 400:
                    br.record_failure()
                    resp.raise_for_status()
                br.record_success()
                if not text.strip():
                    return None, dict(resp.headers), resp.status_code
                ctype = resp.headers.get("content-type", "")
                if "json" in ctype or text.lstrip().startswith(("{", "[")):
                    return resp.json(), dict(resp.headers), resp.status_code
                return text, dict(resp.headers), resp.status_code
            except BlockSignalError:
                raise
            except Exception as exc:
                last_exc = exc
                br.record_failure()
                await asyncio.sleep((2**attempt) + random.random())  # noqa: S311
            finally:
                _global_limiter.release(host)
        assert last_exc is not None
        raise last_exc
    finally:
        if owns:
            await client.aclose()
