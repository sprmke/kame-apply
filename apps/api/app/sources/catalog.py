"""Built-in source catalog rows (seeded)."""

from __future__ import annotations

from typing import Any

from kame_core.sources import list_adapters
from kame_core.sources.registry import get_adapter

COUNTRY_COVERAGE: list[dict[str, str]] = [
    {
        "country": "REMOTE",
        "source_key": "remotive",
        "coverage": "strong",
        "note": "Remote worldwide",
    },
    {
        "country": "REMOTE",
        "source_key": "remoteok",
        "coverage": "strong",
        "note": "Remote worldwide",
    },
    {"country": "REMOTE", "source_key": "himalayas", "coverage": "strong", "note": "Remote"},
    {"country": "US", "source_key": "muse", "coverage": "partial", "note": "US-heavy"},
    {"country": "DE", "source_key": "arbeitnow", "coverage": "strong", "note": "EU/DE"},
    {"country": "EU", "source_key": "arbeitnow", "coverage": "partial", "note": "EU"},
    {"country": "PH", "source_key": "remotive", "coverage": "thin", "note": "Use alerts + clipper"},
]


def catalog_rows() -> list[dict[str, Any]]:
    from kame_core.sources import adapters as _a  # noqa: F401

    rows = []
    for key in list_adapters():
        meta = get_adapter(key).meta
        rows.append(
            {
                "key": meta.key,
                "name": meta.name,
                "kind": meta.layer,
                "adapter": meta.key,
                "terms_note": meta.terms_note,
                "enabled_global": meta.layer != "personal",
            }
        )
    return rows
