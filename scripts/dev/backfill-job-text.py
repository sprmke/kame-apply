"""One-shot: rebuild `jobs.description_text` from the stored HTML.

Older feed ingests kept escaped entities such as `&lt;h3&gt;` in the text. New ingests are
clean; this script repairs existing rows. Run with the owner/migration URL:

    MIGRATION_DATABASE_URL=... uv run python scripts/dev/backfill-job-text.py --dry-run
    MIGRATION_DATABASE_URL=... uv run python scripts/dev/backfill-job-text.py
"""

from __future__ import annotations

import os
import sys
from html import unescape

import psycopg

from kame_core.sources.textutil import html_to_text


def main() -> int:
    url = os.environ.get("MIGRATION_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        print("Set MIGRATION_DATABASE_URL or DATABASE_URL", file=sys.stderr)
        return 2
    dry_run = "--dry-run" in sys.argv

    with psycopg.connect(url.replace("+asyncpg", "")) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, description_html, description_text FROM jobs")
            updates: list[tuple[str, object]] = []
            for job_id, description_html, description_text in cur.fetchall():
                cleaned = (
                    html_to_text(description_html or "")
                    if description_html
                    else unescape(description_text or "")
                )
                if cleaned and cleaned != (description_text or ""):
                    updates.append((cleaned, job_id))

            if dry_run:
                print(f"would update {len(updates)} job rows")
                return 0

            if updates:
                cur.executemany("UPDATE jobs SET description_text = %s WHERE id = %s", updates)
        conn.commit()

    print(f"updated {len(updates)} job rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
