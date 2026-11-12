"""Resolve packs into the manifest a page reads.

Rules: General is the base layer; a pack overrides it. Global pages show the union of enabled
packs, so a hidden control is hidden only when every enabled pack hides it. Hiding is UX only:
the API still accepts the saved value.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from app.industries.packs.general import GENERAL
from app.industries.registry import BASE_INDUSTRY, get_pack
from app.industries.schema import CRITERIA_FIELDS, IndustryPack

FieldState = Literal["visible", "collapsed", "hidden"]
_RANK: dict[str, int] = {"hidden": 0, "collapsed": 1, "visible": 2}
_BY_RANK: dict[int, FieldState] = {0: "hidden", 1: "collapsed", 2: "visible"}

# Everything the web needs to render a criteria page without knowing which pack is active.
Manifest = dict[str, Any]


def _merge_groups(
    base: dict[str, tuple[str, ...]], patch: dict[str, tuple[str, ...]]
) -> dict[str, list[str]]:
    """A pack's groups replace the base ordering; base fields it omits move to More."""
    if not patch:
        groups = {key: list(values) for key, values in base.items()}
    else:
        groups = {key: list(values) for key, values in patch.items()}
        seen = {field_id for values in groups.values() for field_id in values}
        for key, values in base.items():
            for field_id in values:
                if field_id in seen:
                    continue
                groups.setdefault(key if key in groups else "more", []).append(field_id)
                seen.add(field_id)
    seen = set()
    ordered: dict[str, list[str]] = {}
    for key, values in groups.items():
        kept = []
        for field_id in values:
            if field_id in seen:
                continue
            seen.add(field_id)
            kept.append(field_id)
        ordered[key] = kept
    missing = [field_id for field_id in CRITERIA_FIELDS if field_id not in seen]
    if missing:
        ordered.setdefault("more", []).extend(sorted(missing))
    return ordered


def resolve_pack(pack: IndustryPack) -> Manifest:
    """One pack's manifest: its own pages, with General underneath."""
    base = GENERAL
    if pack.key == BASE_INDUSTRY:
        states = dict(base.ui.states)
        groups = _merge_groups(base.ui.groups, {})
        labels = dict(base.ui.labels)
        profile_sections = list(base.ui.profile_sections)
        nav = dict(base.ui.nav)
    else:
        states = {**base.ui.states, **pack.ui.states}
        groups = _merge_groups(base.ui.groups, pack.ui.groups)
        labels = {**base.ui.labels, **pack.ui.labels}
        profile_sections = list(pack.ui.profile_sections or base.ui.profile_sections)
        nav = {**base.ui.nav, **pack.ui.nav}

    return {
        "key": pack.key,
        "version": pack.version,
        "label_key": pack.label_key,
        "icon": pack.icon,
        "states": states,
        "groups": [{"key": group, "fields": fields} for group, fields in groups.items() if fields],
        "labels": labels,
        "profile_sections": profile_sections,
        "nav": nav,
        "facets": [
            {
                "key": facet.key,
                "label_key": facet.label_key,
                "kind": facet.kind,
                "options": [
                    {"key": option.key, "label_key": option.label_key} for option in facet.options
                ],
                "group": facet.group,
                "match": {
                    "filter": facet.match.filter,
                    "boost": facet.match.boost,
                    "ledger_only": facet.match.ledger_only,
                },
            }
            for facet in pack.facets
            if "criteria" in facet.applies_to
        ],
        "features": pack.features.model_dump(),
        "seniority_ladder": [
            {"key": step.key, "label_key": step.label_key, "maps_to": step.maps_to}
            for step in pack.seniority_ladder
        ],
        "criteria_defaults": pack.criteria_defaults.model_dump(),
    }


def _union_state(states: Iterable[str]) -> FieldState:
    return _BY_RANK[max((_RANK.get(state, 1) for state in states), default=1)]


def resolve_workspace(enabled: Iterable[IndustryPack], *, primary_key: str) -> Manifest:
    """Union manifest for global pages (Profile, Answers, Today)."""
    packs = list(enabled) or [GENERAL]
    primary = next((p for p in packs if p.key == primary_key), packs[0])
    manifests = {pack.key: resolve_pack(pack) for pack in packs}

    field_states: dict[str, FieldState] = {}
    for field_id in CRITERIA_FIELDS:
        field_states[field_id] = _union_state(
            manifest["states"].get(field_id, "visible") for manifest in manifests.values()
        )

    primary_manifest = manifests[primary.key]
    groups = _merge_groups(
        {item["key"]: tuple(item["fields"]) for item in primary_manifest["groups"]},
        {},
    )
    seen = {field_id for fields in groups.values() for field_id in fields}
    for pack in packs:
        for item in manifests[pack.key]["groups"]:
            for field_id in item["fields"]:
                if field_id in seen:
                    continue
                groups.setdefault(item["key"], []).append(field_id)
                seen.add(field_id)
    for field_id in CRITERIA_FIELDS:
        if field_id in seen:
            continue
        groups.setdefault("more", []).append(field_id)
        seen.add(field_id)

    labels: dict[str, str] = {}
    for pack in [primary, *[p for p in packs if p.key != primary.key]]:
        for field_id, label_key in manifests[pack.key]["labels"].items():
            labels.setdefault(field_id, label_key)

    profile_sections: list[str] = []
    for pack in [primary, *[p for p in packs if p.key != primary.key]]:
        for section in manifests[pack.key]["profile_sections"]:
            if section not in profile_sections:
                profile_sections.append(section)

    nav: dict[str, bool] = {}
    for manifest in manifests.values():
        for key, visible in manifest["nav"].items():
            nav[key] = bool(nav.get(key) or visible)

    facets: list[dict[str, Any]] = []
    seen_facets: set[str] = set()
    for pack in packs:
        for facet in manifests[pack.key]["facets"]:
            if facet["key"] in seen_facets:
                continue
            seen_facets.add(facet["key"])
            facets.append(facet)

    features: dict[str, bool] = {}
    for manifest in manifests.values():
        for key, enabled_flag in manifest["features"].items():
            features[key] = bool(features.get(key) or enabled_flag)

    return {
        "key": primary.key,
        "version": primary.version,
        "label_key": primary.label_key,
        "icon": primary.icon,
        "states": field_states,
        "groups": [{"key": group, "fields": fields} for group, fields in groups.items() if fields],
        "labels": labels,
        "profile_sections": profile_sections,
        "nav": nav,
        "facets": facets,
        "features": features,
    }


def manifest_for_key(
    key: str, *, custom_packs: dict[str, dict[str, Any]] | None = None
) -> Manifest:
    pack = get_pack(key, custom=(custom_packs or {}).get(key))
    if pack is None:
        pack = GENERAL
    return resolve_pack(pack)
