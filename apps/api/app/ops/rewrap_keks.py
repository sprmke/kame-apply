"""Re-wrap every workspace data key under a new master key (KEK rotation).

    MASTER_KEK=<new> MASTER_KEK_PREVIOUS=<old> uv run python -m app.ops.rewrap_keks [--dry-run]

Connects as the migration/owner role (MIGRATION_DATABASE_URL). Provider keys are not touched: only
`workspace_keys.wrapped_dek` changes. Idempotent: rows already wrapped under the new key are
skipped. Run once, verify, then remove MASTER_KEK_PREVIOUS from the environment.
"""

import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.ai import crypto
from app.core.config import Settings
from app.core.errors import AppError


async def rewrap(new_b64: str, old_b64: str, url: str, *, dry_run: bool = False) -> tuple[int, int]:
    """Return (rewrapped, already_current)."""
    new, old = crypto.parse_kek(new_b64), crypto.parse_kek(old_b64)
    if new == old:
        raise SystemExit("MASTER_KEK and MASTER_KEK_PREVIOUS are identical")
    engine = create_async_engine(url)
    done = skipped = 0
    async with engine.begin() as conn:
        rows = (
            await conn.execute(
                text("SELECT workspace_id, wrapped_dek, kek_version FROM workspace_keys FOR UPDATE")
            )
        ).all()
        for ws_id, wrapped, version in rows:
            try:
                crypto.unwrap_dek(new, bytes(wrapped), ws_id)
                skipped += 1
                continue
            except AppError:
                pass
            dek = crypto.unwrap_dek(old, bytes(wrapped), ws_id)  # raises if neither key fits
            if not dry_run:
                await conn.execute(
                    text(
                        "UPDATE workspace_keys SET wrapped_dek = :w, kek_version = :v "
                        "WHERE workspace_id = :id"
                    ),
                    {"w": crypto.wrap_dek(new, dek, ws_id), "v": version + 1, "id": ws_id},
                )
            done += 1
    await engine.dispose()
    return done, skipped


def main() -> None:
    new, old = os.environ.get("MASTER_KEK"), os.environ.get("MASTER_KEK_PREVIOUS")
    if not new or not old:
        raise SystemExit("Set MASTER_KEK (new) and MASTER_KEK_PREVIOUS (old)")
    url = Settings().migration_database_url
    done, skipped = asyncio.run(rewrap(new, old, url, dry_run="--dry-run" in sys.argv))
    print(f"rewrapped={done} already_current={skipped}")


if __name__ == "__main__":
    main()
