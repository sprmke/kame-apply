"""Search query contract shared by Layer 4 adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SearchQuery:
    keywords: str
    location: str = ""
    country: str = ""
    radius_km: int | None = None
    category: str | None = None
    posted_within_days: int | None = None
    page: int = 1

    @classmethod
    def from_params(cls, params: Any) -> SearchQuery:
        get = params.get
        return cls(
            keywords=str(get("keywords") or "").strip(),
            location=str(get("location") or "").strip(),
            country=str(get("country") or "").strip().upper(),
            radius_km=get("radius_km"),
            category=get("category"),
            posted_within_days=get("posted_within_days"),
            page=int(get("page") or 1),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "keywords": self.keywords,
            "location": self.location,
            "country": self.country,
            "radius_km": self.radius_km,
            "category": self.category,
            "posted_within_days": self.posted_within_days,
            "page": self.page,
        }


@dataclass(slots=True)
class SearchResult:
    jobs: list[Any] = field(default_factory=list)
    total: int | None = None
