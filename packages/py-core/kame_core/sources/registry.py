"""Adapter registry."""

from __future__ import annotations

from typing import Any

from kame_core.sources.base import SourceAdapter

_REGISTRY: dict[str, type] = {}


def register_adapter(cls: type) -> type:
    meta = getattr(cls, "meta", None)
    if meta is None:
        raise TypeError(f"{cls} missing meta")
    _REGISTRY[meta.key] = cls
    return cls


def get_adapter(key: str, **kwargs: Any) -> SourceAdapter:
    if key not in _REGISTRY:
        # Lazy import default adapters once
        from kame_core.sources import adapters as _adapters  # noqa: F401

    try:
        cls = _REGISTRY[key]
    except KeyError as exc:
        raise KeyError(f"unknown adapter: {key}") from exc
    return cls(**kwargs)  # type: ignore[call-arg]


def list_adapters() -> list[str]:
    from kame_core.sources import adapters as _adapters  # noqa: F401

    return sorted(_REGISTRY)
