"""Adapter contracts for job discovery (PRD P5, job-site-access)."""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol

Layer = Literal["ats", "board", "career_page", "email", "clip", "personal"]


@dataclass(frozen=True, slots=True)
class AdapterMeta:
    key: str
    name: str
    layer: Layer
    terms_note: str
    contact_ua: str = "KameApplyBot/0.1 (+https://kame.apply/bot)"
    countries: tuple[str, ...] = ()
    auth: Literal["none", "api_key"] = "none"
    rate_limit_per_minute: int = 30
    concurrency: int = 1


@dataclass(slots=True)
class RawJob:
    """Normalized-enough posting from a single source before persistence."""

    external_id: str
    source_key: str
    title: str
    company_name: str
    url: str
    apply_url: str
    description_html: str = ""
    description_text: str = ""
    location_text: str = ""
    remote: bool | None = None
    employment_type: str = ""
    salary_text: str = ""
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    salary_period: str | None = None
    posted_at: datetime | None = None
    expires_at: datetime | None = None
    ats: str | None = None
    board_slug: str | None = None
    company_domain: str | None = None
    allowed_countries: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SourceHealth:
    ok: bool
    latency_ms: float | None = None
    items: int = 0
    error: str | None = None
    block_signal: bool = False


class SourceAdapter(Protocol):
    meta: AdapterMeta

    def discover(self, params: Mapping[str, Any]) -> AsyncIterator[RawJob]:
        """Yield jobs for the given board/query params. Must not evade blocks."""
        ...

    async def fetch_detail(self, ref: Mapping[str, Any]) -> RawJob | None: ...

    async def health(self) -> SourceHealth: ...
