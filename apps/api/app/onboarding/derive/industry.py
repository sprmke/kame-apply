"""Industry hook. Returns None until industry packs ship (multi-industry-support S8)."""

from __future__ import annotations

from typing import Any


def detect(reading: Any) -> None:
    return None
