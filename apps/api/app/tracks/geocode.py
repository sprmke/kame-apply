"""Nominatim geocoding with in-process + DB cache. Respects usage policy (1 req/s, UA)."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

log = structlog.get_logger()

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "KameApply/0.1 (https://github.com/kame-apply; geocode for job search criteria)"
_MIN_INTERVAL_S = 1.05
_lock = asyncio.Lock()
_last_call = 0.0


@dataclass(frozen=True)
class GeocodeResult:
    place: str
    lat: float
    lon: float
    country: str | None
    display_name: str
    cached: bool


async def geocode_place(
    session: AsyncSession,
    place: str,
    *,
    http_client: httpx.AsyncClient | None = None,
    allow_network: bool = True,
) -> GeocodeResult | None:
    from app.tracks.models import GeocodeCache

    key = place.strip()
    if not key:
        return None
    existing = (
        await session.execute(select(GeocodeCache).where(GeocodeCache.query_key == key.casefold()))
    ).scalar_one_or_none()
    if existing is not None:
        return GeocodeResult(
            place=key,
            lat=float(existing.lat),
            lon=float(existing.lon),
            country=existing.country,
            display_name=existing.display_name,
            cached=True,
        )
    if not allow_network:
        return None

    payload = await _nominatim(key, client=http_client)
    if payload is None:
        return None
    row = GeocodeCache(
        query_key=key.casefold(),
        query=key,
        lat=payload["lat"],
        lon=payload["lon"],
        country=payload.get("country"),
        display_name=payload["display_name"],
        raw=payload.get("raw") or {},
    )
    session.add(row)
    await session.flush()
    return GeocodeResult(
        place=key,
        lat=float(row.lat),
        lon=float(row.lon),
        country=row.country,
        display_name=row.display_name,
        cached=False,
    )


async def _nominatim(
    place: str, *, client: httpx.AsyncClient | None = None
) -> dict[str, Any] | None:
    global _last_call
    params = urlencode({"q": place, "format": "json", "limit": 1, "addressdetails": 1})
    url = f"{NOMINATIM_URL}?{params}"
    owns = client is None
    client = client or httpx.AsyncClient(timeout=20.0)
    try:
        async with _lock:
            wait = _MIN_INTERVAL_S - (time.monotonic() - _last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            resp = await client.get(url, headers={"User-Agent": USER_AGENT})
            _last_call = time.monotonic()
        if resp.status_code != 200:
            log.warning("geocode_http", status=resp.status_code)
            return None
        data = resp.json()
        if not data:
            return None
        hit = data[0]
        addr = hit.get("address") or {}
        country = addr.get("country_code")
        if country:
            country = str(country).upper()[:2]
        return {
            "lat": float(hit["lat"]),
            "lon": float(hit["lon"]),
            "country": country,
            "display_name": hit.get("display_name") or place,
            "raw": hit,
        }
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        log.warning("geocode_failed", error=type(exc).__name__)
        return None
    finally:
        if owns:
            await client.aclose()
