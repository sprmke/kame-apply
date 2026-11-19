"""Layer 4: keyword + location search, shared cache, and Track linking.

Search providers are platform keys, never user keys. A provider runs only after a human confirms
its terms (`SEARCH_TERMS_ACKNOWLEDGED`) or when a fixture is supplied for tests. A missing key
disables that provider cleanly. Results are cached globally so fifty workspaces searching
"cook Manila" cost one call per window.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import Settings
from app.core.security import WorkspaceContext
from app.industries.schema import IndustryPack
from app.industries.service import pack_for_track
from app.jobs.ingest import upsert_raw_job
from app.jobs.link import link_track_job
from app.jobs.models import DiscoveryRun
from app.sources.models import Source, SourceQueryCache
from app.tracks.criteria import CriteriaV1, LocationFilter, criteria_from_dict
from app.tracks.models import Track, TrackCriteria
from kame_core.sources import get_adapter, list_adapters
from kame_core.sources.base import AdapterMeta, RawJob
from kame_core.sources.http import BlockSignalError

_SECRET_PARAM = re.compile(r"(?i)(app_key|app_id|api_key|key)=([^&\s]+)")


def _safe_error(exc: Exception) -> str:
    """Store a provider failure without URLs, query strings, or API keys."""
    name = type(exc).__name__
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    request = getattr(exc, "request", None)
    url = getattr(request, "url", None)
    host = getattr(url, "host", None)
    detail = f"{name}"
    if status is not None:
        detail += f" status={status}"
    if host:
        detail += f" host={host}"
    return _SECRET_PARAM.sub(r"\1=***", detail)[:500]


def _hash(query: dict[str, Any]) -> str:
    blob = json.dumps(query, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


async def _ensure_source(session, meta: AdapterMeta) -> Source:
    source = (
        await session.execute(select(Source).where(Source.key == meta.key))
    ).scalar_one_or_none()
    if source is not None:
        return source
    source = Source(
        key=meta.key,
        name=meta.name,
        kind=meta.layer,
        adapter=meta.key,
        terms_note=meta.terms_note,
        enabled_global=True,
        meta={
            "countries": list(meta.countries),
            "terms_verified": meta.terms_verified,
            "terms_url": meta.terms_url,
        },
    )
    session.add(source)
    await session.flush()
    return source


DEFAULT_SEARCH_PLACE = "Philippines"
DEFAULT_SEARCH_COUNTRY = "PH"
DEFAULT_SEARCH_RADIUS_KM = 100


def plan_queries(
    track: Track,
    criteria: CriteriaV1,
    pack: IndustryPack,
    *,
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Build a small set of keyword + location queries from the Track, never inventing places.

    No location means the home market: the Philippines with a 100 km radius. Every location the
    person adds becomes its own query, so several places widen the search instead of replacing it.
    """
    titles = [t.title for t in criteria.titles if not t.exclude][:3] or [track.name]
    countries = {loc.country.upper() for loc in criteria.locations if loc.country}
    if len(countries) != 1:
        countries = set()
    country = next(iter(countries), "")
    category_map = pack.sources.adzuna_categories
    home = [
        LocationFilter(
            place=DEFAULT_SEARCH_PLACE,
            country=DEFAULT_SEARCH_COUNTRY,
            radius_km=DEFAULT_SEARCH_RADIUS_KM,
        )
    ]
    out: list[dict[str, Any]] = []
    for title in titles:
        if criteria.locations:
            places = criteria.locations
        elif criteria.remote_eligibility and criteria.remote_eligibility.anywhere:
            places = []
        else:
            places = home
        if places:
            for loc in places:
                out.append(
                    {
                        "keywords": title,
                        "location": loc.place,
                        "country": (loc.country or country or "").upper(),
                        "radius_km": loc.radius_km,
                        "category": category_map.get((loc.country or "").upper()),
                        "posted_within_days": criteria.posting_max_age_days,
                        "page": 1,
                    }
                )
        else:
            out.append(
                {
                    "keywords": f"{title} remote",
                    "location": "",
                    "country": country,
                    "category": category_map.get(country),
                    "posted_within_days": criteria.posting_max_age_days,
                    "page": 1,
                }
            )
    # Deduplicate and cap so one Track cannot fan out across dozens of paid calls.
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for query in out:
        key = _hash(query)
        if key in seen:
            continue
        seen.add(key)
        unique.append(query)
    return unique[:limit]


def _adapter_keys(pack: IndustryPack) -> list[str]:
    available = set(list_adapters())
    keys = [key for key in pack.sources.adapters if key.startswith("search_")]
    if not keys:
        keys = sorted(key for key in available if key.startswith("search_"))
    return [key for key in keys if key in available]


def _supports_country(meta: AdapterMeta, country: str) -> bool:
    return not country or not meta.countries or country.upper() in meta.countries


def _configured(meta: AdapterMeta, settings: Settings) -> bool:
    if meta.key == "search_jooble":
        has_key = bool(
            settings.jooble_api_key or settings.jooble_api_key_ph or settings.jooble_api_key_ae
        )
    elif meta.key == "search_adzuna":
        has_key = bool(settings.adzuna_app_id and settings.adzuna_app_key)
    else:
        has_key = False
    if not has_key:
        return False
    return bool(meta.terms_verified or settings.search_terms_acknowledged)


def _adapter_kwargs(meta: AdapterMeta, settings: Settings, fixture_root: Path | None):
    kwargs: dict[str, Any] = {}
    if fixture_root is not None and (fixture_root / meta.key).is_dir():
        kwargs["fixture_dir"] = fixture_root / meta.key
    if meta.key == "search_jooble":
        kwargs["api_key"] = settings.jooble_api_key
        kwargs["api_keys"] = {
            "PH": settings.jooble_api_key_ph,
            "AE": settings.jooble_api_key_ae,
        }
    elif meta.key == "search_adzuna":
        kwargs["app_id"] = settings.adzuna_app_id
        kwargs["app_key"] = settings.adzuna_app_key
    return kwargs


def _raw_to_payload(raw: RawJob) -> dict[str, Any]:
    data = asdict(raw)
    for key in ("posted_at", "expires_at"):
        value = data.get(key)
        if isinstance(value, datetime):
            data[key] = value.isoformat()
    # The cache is global; keep one row bounded so a verbose feed cannot store megabytes per query.
    for key in ("description_html", "description_text"):
        value = data.get(key)
        if isinstance(value, str) and len(value) > 20_000:
            data[key] = value[:20_000]
    return data


def _raw_from_payload(data: dict[str, Any]) -> RawJob:
    clean = dict(data)
    for key in ("posted_at", "expires_at"):
        value = clean.get(key)
        if isinstance(value, str) and value:
            try:
                clean[key] = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                clean[key] = None
    return RawJob(**clean)


async def _cached(
    session, source_key: str, query_hash: str, now: datetime
) -> list[dict[str, Any]] | None:
    row = (
        await session.execute(
            select(SourceQueryCache).where(
                SourceQueryCache.source_key == source_key,
                SourceQueryCache.query_hash == query_hash,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    if row.expires_at is not None and row.expires_at <= now:
        return None
    return list(row.payload or [])


async def _store_cache(
    session,
    source_key: str,
    query_hash: str,
    payload: list[dict[str, Any]],
    *,
    ttl_hours: int,
    now: datetime,
) -> None:
    stmt = (
        pg_insert(SourceQueryCache)
        .values(
            source_key=source_key,
            query_hash=query_hash,
            payload=payload,
            fetched_at=now,
            expires_at=now + timedelta(hours=ttl_hours),
        )
        .on_conflict_do_update(
            constraint="uq_source_query_cache",
            set_={
                "payload": payload,
                "fetched_at": now,
                "expires_at": now + timedelta(hours=ttl_hours),
            },
        )
    )
    await session.execute(stmt)


async def run_search_sources(
    ctx: WorkspaceContext,
    *,
    track: Track,
    run: DiscoveryRun,
    progress: dict[str, Any],
    fixture_root: Path | None,
    settings: Settings,
) -> None:
    if not settings.search_sources_enabled:
        return
    crit = (
        await ctx.session.execute(select(TrackCriteria).where(TrackCriteria.track_id == track.id))
    ).scalar_one_or_none()
    criteria = criteria_from_dict(crit.structured if crit else {})
    pack = await pack_for_track(ctx.session, workspace_id=ctx.workspace_id, industry=track.industry)
    queries = plan_queries(track, criteria, pack, limit=settings.search_queries_per_track)
    if not queries:
        return
    now = datetime.now(UTC)
    for key in _adapter_keys(pack):
        meta = get_adapter(key).meta
        source = await _ensure_source(ctx.session, meta)
        if source.circuit_open or not source.enabled_global:
            continue
        configured = _configured(meta, settings)
        fixture_mode = fixture_root is not None and (fixture_root / key).is_dir()
        if not configured and not fixture_mode:
            continue
        kwargs = _adapter_kwargs(meta, settings, fixture_root)
        for query in queries:
            if not _supports_country(meta, str(query.get("country") or "")):
                continue
            qhash = _hash(query)
            payload = await _cached(ctx.session, key, qhash, now)
            if payload is None:
                adapter = get_adapter(key, **kwargs)
                collected: list[dict[str, Any]] = []
                try:
                    async for raw in adapter.discover(query):
                        collected.append(_raw_to_payload(raw))
                        if len(collected) >= 100:
                            break
                    await _store_cache(
                        ctx.session,
                        key,
                        qhash,
                        collected,
                        ttl_hours=settings.source_query_ttl_hours,
                        now=now,
                    )
                    source.last_success_at = now
                    source.success_count = (source.success_count or 0) + 1
                except BlockSignalError as exc:
                    source.circuit_open = True
                    source.block_signals = (source.block_signals or 0) + 1
                    source.last_error = _safe_error(exc)
                    source.last_error_at = now
                    progress["search_blocked"] = int(progress.get("search_blocked") or 0) + 1
                    break
                except Exception as exc:
                    source.last_error = _safe_error(exc)
                    source.last_error_at = now
                    source.error_count = (source.error_count or 0) + 1
                    progress["search_errors"] = int(progress.get("search_errors") or 0) + 1
                    continue
                payload = collected
            progress["search_queries"] = int(progress.get("search_queries") or 0) + 1
            for item in payload:
                try:
                    raw = _raw_from_payload(item)
                    async with ctx.session.begin_nested():
                        job, created = await upsert_raw_job(ctx.session, raw)
                except Exception:
                    progress["skipped"] = int(progress.get("skipped") or 0) + 1
                    continue
                progress["jobs_found"] = int(progress.get("jobs_found") or 0) + 1
                if created:
                    progress["jobs_new"] = int(progress.get("jobs_new") or 0) + 1
                linked = await link_track_job(
                    ctx.session,
                    workspace_id=ctx.workspace_id,
                    track_id=track.id,
                    job=job,
                    structured=crit.structured if crit else {},
                )
                if linked:
                    progress["linked"] = int(progress.get("linked") or 0) + 1
            run.progress = dict(progress)
            await ctx.session.flush()


def search_queries_for_track(
    track: Track, criteria: CriteriaV1, pack: IndustryPack
) -> list[dict[str, Any]]:
    """Public helper for the Search > Where we look view."""
    return plan_queries(track, criteria, pack)


def adapter_plan(pack: IndustryPack, settings: Settings) -> list[dict[str, Any]]:
    """What would run for this field today, including honest configuration status."""
    rows: list[dict[str, Any]] = []
    for key in _adapter_keys(pack):
        meta = get_adapter(key).meta
        rows.append(
            {
                "key": key,
                "name": meta.name,
                "terms_note": meta.terms_note,
                "terms_url": meta.terms_url,
                "configured": _configured(meta, settings),
                "countries": list(meta.countries),
            }
        )
    return rows
