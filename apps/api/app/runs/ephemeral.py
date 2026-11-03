"""One-shot in-memory vault for values the human types at a sensitive checkpoint.

Sensitive values must never be stored (pii-guard.mdc): not in Postgres, not in logs, not in the
activity log. The runner asks for the value once, immediately after the decision, and the entry is
removed on read. Entries also expire so an abandoned run cannot leave a value in memory.

Process-local by design. The API must run a single worker process for the runner hand-off (the
deployment uses one uvicorn process); a multi-worker deployment would need a shared ephemeral
store, which this project does not run (no Redis).
"""

from __future__ import annotations

import time

DEFAULT_TTL_SECONDS = 300.0

_VAULT: dict[str, tuple[str, float]] = {}


def put(key: str, value: str, *, ttl: float = DEFAULT_TTL_SECONDS) -> None:
    _VAULT[key] = (value, time.monotonic() + ttl)


def pop(key: str) -> str | None:
    item = _VAULT.pop(key, None)
    if item is None:
        return None
    value, expires = item
    if time.monotonic() > expires:
        return None
    return value


def clear() -> None:
    _VAULT.clear()
