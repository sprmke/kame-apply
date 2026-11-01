"""Human-readable criteria diffs for the pencil update preview."""

from __future__ import annotations

from typing import Any

from app.tracks.criteria import CriteriaV1


def _norm(v: Any) -> Any:
    if isinstance(v, list):
        return [_norm(x) for x in v]
    if isinstance(v, dict):
        return {k: _norm(v[k]) for k in sorted(v)}
    return v


def _path_label(path: str) -> str:
    return path.replace("_", " ").replace(".", " / ")


def diff_criteria(before: CriteriaV1, after: CriteriaV1) -> list[dict[str, Any]]:
    """Return a list of {op, path, before, after, label} changes.

    Empty fields are treated as absent so setting a value from empty is an add.
    """
    a = _norm(before.model_dump(mode="json"))
    b = _norm(after.model_dump(mode="json"))
    changes: list[dict[str, Any]] = []

    def walk(pa: Any, pb: Any, path: str) -> None:
        if pa == pb:
            return
        if isinstance(pa, dict) and isinstance(pb, dict):
            keys = set(pa) | set(pb)
            for k in sorted(keys):
                if k == "schema_version":
                    continue
                walk(pa.get(k), pb.get(k), f"{path}.{k}" if path else k)
            return
        if _is_empty(pa) and not _is_empty(pb):
            changes.append(
                {
                    "op": "add",
                    "path": path,
                    "before": None,
                    "after": pb,
                    "label": f"added: {_describe(path, pb)}",
                }
            )
        elif not _is_empty(pa) and _is_empty(pb):
            changes.append(
                {
                    "op": "remove",
                    "path": path,
                    "before": pa,
                    "after": None,
                    "label": f"removed: {_describe(path, pa)}",
                }
            )
        else:
            changes.append(
                {
                    "op": "change",
                    "path": path,
                    "before": pa,
                    "after": pb,
                    "label": f"changed {_path_label(path)}",
                }
            )

    walk(a, b, "")
    return changes


def _is_empty(v: Any) -> bool:
    if v is None:
        return True
    if v is False:
        return False
    if isinstance(v, (list, dict, str)) and len(v) == 0:
        return True
    if isinstance(v, dict):
        return all(_is_empty(x) for x in v.values())
    return False


def _describe(path: str, value: Any) -> str:
    leaf = path.split(".")[-1] if path else "criteria"
    if leaf == "exclude_agencies" and value is True:
        return "no agencies"
    if isinstance(value, list) and value and all(isinstance(x, str) for x in value):
        return f"{_path_label(path)} ({', '.join(value[:5])})"
    if isinstance(value, list) and value and isinstance(value[0], dict) and "title" in value[0]:
        titles = [x.get("title", "?") for x in value[:5]]
        return ", ".join(titles)
    if isinstance(value, (str, int, float, bool)):
        return f"{_path_label(path)} = {value}"
    return _path_label(path)
