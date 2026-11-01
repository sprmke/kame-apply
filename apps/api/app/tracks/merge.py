"""Merge NL-compiled partial criteria into the current CriteriaV1.

Semantics:
- Only fields present in `patch` (explicitly set) replace or extend current values.
- Lists of strings/titles merge by union unless `replace_paths` says replace.
- Removals come through `removals` (path + value) so the compiler never silently drops fields.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.tracks.criteria import CriteriaV1, SkillSets, TitleSpec, criteria_from_dict


class CriteriaPatch(BaseModel):
    """Partial criteria from the NL compiler. Unset fields are ignored (not cleared)."""

    model_config = ConfigDict(extra="forbid")

    titles: list[TitleSpec] | None = None
    occupations: list[Any] | None = None
    skills: SkillSets | None = None
    seniority: list[str] | None = None
    employment_types: list[str] | None = None
    work_modes: list[str] | None = None
    remote_eligibility: dict[str, Any] | None = None
    locations: list[Any] | None = None
    visa_sponsorship: bool | None = None
    relocation: bool | None = None
    salary: dict[str, Any] | None = None
    companies: dict[str, Any] | None = None
    posting_max_age_days: int | None = None
    languages: list[str] | None = None
    education: str | None = None
    clearance: str | None = None
    keywords: dict[str, Any] | None = None
    min_match_score: int | None = None
    caps: dict[str, Any] | None = None
    # Paths to fully replace instead of merge (e.g. "skills.must").
    replace_paths: list[str] = Field(default_factory=list)
    # Explicit removals: {"path": "skills.must", "value": "Angular"}
    removals: list[dict[str, Any]] = Field(default_factory=list)


def merge_criteria(current: CriteriaV1, patch: CriteriaPatch) -> CriteriaV1:
    data = current.model_dump(mode="json")
    raw = patch.model_dump(mode="json", exclude_none=True)
    replace = set(raw.pop("replace_paths", []) or [])
    removals = raw.pop("removals", []) or []

    for key, value in raw.items():
        if key in ("schema_version",):
            continue
        if key in replace or key not in data:
            data[key] = value
            continue
        if isinstance(value, dict) and isinstance(data.get(key), dict):
            data[key] = _merge_dict(data[key], value, prefix=key, replace=replace)
        elif isinstance(value, list) and isinstance(data.get(key), list):
            data[key] = _merge_list(data[key], value, path=key, replace=replace)
        else:
            data[key] = value

    for rem in removals:
        _apply_removal(data, rem)

    return criteria_from_dict(data)


def _merge_dict(
    base: dict[str, Any], patch: dict[str, Any], *, prefix: str, replace: set[str]
) -> dict[str, Any]:
    out = dict(base)
    for k, v in patch.items():
        path = f"{prefix}.{k}"
        if path in replace or k not in out:
            out[k] = v
        elif isinstance(v, list) and isinstance(out.get(k), list):
            out[k] = _merge_list(out[k], v, path=path, replace=replace)
        elif isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge_dict(out[k], v, prefix=path, replace=replace)
        else:
            out[k] = v
    return out


def _merge_list(base: list[Any], patch: list[Any], *, path: str, replace: set[str]) -> list[Any]:
    if path in replace:
        return list(patch)
    if not patch:
        return list(base)
    if patch and isinstance(patch[0], str):
        seen = {str(x).casefold(): x for x in base}
        for item in patch:
            key = str(item).casefold()
            if key not in seen:
                seen[key] = item
        return list(seen.values())
    if patch and isinstance(patch[0], dict) and "title" in patch[0]:
        by_title = {str(x.get("title", "")).casefold(): x for x in base if isinstance(x, dict)}
        for item in patch:
            key = str(item.get("title", "")).casefold()
            if item.get("exclude"):
                by_title[key] = item
            elif key in by_title and not by_title[key].get("exclude"):
                existing = dict(by_title[key])
                syns = list(existing.get("synonyms") or [])
                for s in item.get("synonyms") or []:
                    if s not in syns:
                        syns.append(s)
                existing["synonyms"] = syns
                by_title[key] = existing
            else:
                by_title[key] = item
        return list(by_title.values())
    # Occupations / locations: union by stable key
    if patch and isinstance(patch[0], dict) and "code" in patch[0]:
        by = {f"{x.get('scheme')}:{x.get('code')}": x for x in base if isinstance(x, dict)}
        for item in patch:
            by[f"{item.get('scheme')}:{item.get('code')}"] = item
        return list(by.values())
    if patch and isinstance(patch[0], dict) and "place" in patch[0]:
        by = {str(x.get("place", "")).casefold(): x for x in base if isinstance(x, dict)}
        for item in patch:
            by[str(item.get("place", "")).casefold()] = item
        return list(by.values())
    return list(patch)


def _apply_removal(data: dict[str, Any], rem: dict[str, Any]) -> None:
    path = str(rem.get("path") or "")
    value = rem.get("value")
    if not path:
        return
    parts = path.split(".")
    cur: Any = data
    for p in parts[:-1]:
        if not isinstance(cur, dict) or p not in cur:
            return
        cur = cur[p]
    leaf = parts[-1]
    if not isinstance(cur, dict) or leaf not in cur:
        return
    target = cur[leaf]
    if isinstance(target, list) and value is not None:
        if target and isinstance(target[0], str):
            cur[leaf] = [x for x in target if str(x).casefold() != str(value).casefold()]
        elif target and isinstance(target[0], dict) and "title" in target[0]:
            cur[leaf] = [
                x for x in target if str(x.get("title", "")).casefold() != str(value).casefold()
            ]
        elif target and isinstance(target[0], dict) and "code" in target[0]:
            cur[leaf] = [x for x in target if str(x.get("code", "")) != str(value)]
    elif value is None:
        if isinstance(target, list):
            cur[leaf] = []
        elif isinstance(target, bool):
            cur[leaf] = False
        else:
            cur[leaf] = None
