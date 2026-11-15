"""Industry pack registry. Packs are code, so the picker and the resolver share one source."""

from __future__ import annotations

from typing import Any

from app.industries.packs.extra import EXTRA_PACKS
from app.industries.packs.general import GENERAL
from app.industries.packs.hospitality import HOSPITALITY
from app.industries.packs.technology import TECHNOLOGY
from app.industries.schema import IndustryPack

PACKS: tuple[IndustryPack, ...] = (GENERAL, TECHNOLOGY, HOSPITALITY, *EXTRA_PACKS)
DEFAULT_WORKSPACE_INDUSTRY = "technology"
BASE_INDUSTRY = "general"

_BY_KEY: dict[str, IndustryPack] = {p.key: p for p in PACKS}
# Template industries that already have a curated pack. Everything else uses General until its
# pack ships.
_TEMPLATE_PACKS = {
    "technology": "technology",
    "hospitality": "hospitality",
    "healthcare": "healthcare",
    "engineering": "engineering",
    "trades": "trades",
    "education": "education",
    "finance": "finance",
    "sales": "sales_marketing",
    "marketing": "sales_marketing",
}


def get_pack(key: str, *, custom: dict[str, Any] | None = None) -> IndustryPack | None:
    """Resolve a curated pack, or validate a stored custom pack against the same schema."""
    if key in _BY_KEY:
        return _BY_KEY[key]
    if custom is None:
        return None
    pack = IndustryPack.model_validate(custom)
    if pack.key != key:
        return None
    return pack


def require_pack(key: str, *, custom: dict[str, Any] | None = None) -> IndustryPack:
    pack = get_pack(key, custom=custom)
    if pack is None:
        raise KeyError(f"unknown industry pack: {key}")
    return pack


def is_known(key: str) -> bool:
    return key in _BY_KEY


def list_packs() -> tuple[IndustryPack, ...]:
    return PACKS


def pack_for_template(template_industry: str | None) -> str:
    if not template_industry:
        return DEFAULT_WORKSPACE_INDUSTRY
    return _TEMPLATE_PACKS.get(template_industry, BASE_INDUSTRY)
