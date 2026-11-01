"""Shared adapter helpers."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable, Mapping
from pathlib import Path
from typing import Any

from kame_core.sources.base import RawJob, SourceHealth
from kame_core.sources.http import BlockSignalError, fetch_json


def fixture_loader(path: Path | None) -> Callable[[str], Any] | None:
    if path is None:
        return None

    def load(name: str) -> Any:
        data = (path / name).read_text(encoding="utf-8")
        if name.endswith(".json"):
            return json.loads(data)
        return data

    return load


async def iter_from_payload(
    items: list[RawJob],
) -> AsyncIterator[RawJob]:
    for item in items:
        yield item


async def health_ping(url: str, *, fixture: Any | None = None) -> SourceHealth:
    if fixture is not None:
        return SourceHealth(ok=True, latency_ms=1.0, items=1)
    try:
        import time

        t0 = time.perf_counter()
        await fetch_json(url)
        return SourceHealth(ok=True, latency_ms=(time.perf_counter() - t0) * 1000)
    except BlockSignalError as exc:
        return SourceHealth(ok=False, error=str(exc), block_signal=True)
    except Exception as exc:
        return SourceHealth(ok=False, error=str(exc))


def require_slug(params: Mapping[str, Any]) -> str:
    slug = str(params.get("slug") or "").strip()
    if not slug:
        raise ValueError("slug is required")
    return slug
