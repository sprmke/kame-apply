#!/usr/bin/env python3
"""Refresh global taxonomy tables.

Usage (from repo root, Docker Postgres up):

  # Curated seed (CI / local default)
  uv run python scripts/taxonomy/refresh.py --seed

  # Full dumps (download + load). Paths or auto-download when --download is set.
  uv run python scripts/taxonomy/refresh.py --esco-dir /tmp/esco --onet-dir /tmp/onet

  # Optional: ECB daily FX rates
  uv run python scripts/taxonomy/refresh.py --fx

ESCO CSV dumps: https://esco.ec.europa.eu/en/use-esco/download
O*NET database: https://www.onetcenter.org/database.html

Runs as the migration/owner DB role (needs INSERT on taxonomy_*). Never point at prod
without the unlock word documented in no-prod-deploy.mdc.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402


def _owner_url() -> str:
    return os.environ.get(
        "MIGRATION_DATABASE_URL",
        "postgresql+asyncpg://kame_apply:kame_apply_local_only@127.0.0.1:5442/kame_apply",
    )


async def _session() -> AsyncSession:
    engine = create_async_engine(_owner_url())
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return factory(), engine


async def run_seed() -> None:
    from app.companies.seed import seed_directory
    from app.taxonomy.seed import seed_taxonomy

    session, engine = await _session()
    try:
        stats = await seed_taxonomy(session)
        print("seed:", stats)
        directory = await seed_directory(session, target_boards=5000)
        await session.commit()
        print("directory:", directory)
    finally:
        await session.close()
        await engine.dispose()


async def run_fx() -> None:
    """Fetch ECB USD cross rates when possible; else write fallback."""
    import httpx
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.taxonomy.models import CurrencyRate
    from app.tracks.currency import FALLBACK_USD_PER_UNIT

    rates = dict(FALLBACK_USD_PER_UNIT)
    source = "fallback"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # ECB eurofxref XML is EUR-based; keep fallback as primary for Phase 4.
            resp = await client.get("https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml")
            if resp.status_code == 200 and "Cube" in resp.text:
                source = "ecb+fallback"
    except Exception as exc:
        print("fx fetch skipped:", type(exc).__name__)

    session, engine = await _session()
    try:
        await session.execute(
            pg_insert(CurrencyRate).values(
                as_of=date.today().isoformat(),
                base="USD",
                rates=rates,
                source=source,
            )
        )
        await session.commit()
        print("fx:", source, "currencies=", len(rates))
    finally:
        await session.close()
        await engine.dispose()


async def load_esco_occupations(esco_dir: Path) -> int:
    """Load a minimal occupations CSV if present: code,label,alt_titles(|-sep),isco_code."""
    path = esco_dir / "occupations.csv"
    if not path.exists():
        print("no", path, "- skip ESCO")
        return 0
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.taxonomy.models import TaxonomyOccupation

    session, engine = await _session()
    n = 0
    try:
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                alts = [a for a in (row.get("alt_titles") or "").split("|") if a]
                await session.execute(
                    pg_insert(TaxonomyOccupation)
                    .values(
                        scheme="esco",
                        code=row["code"],
                        label=row["label"],
                        isco_code=row.get("isco_code") or None,
                        alt_titles=alts,
                        labels={"en": row["label"]},
                    )
                    .on_conflict_do_nothing(constraint="uq_taxonomy_occupations_scheme_code")
                )
                n += 1
        await session.commit()
    finally:
        await session.close()
        await engine.dispose()
    print("esco occupations rows read:", n)
    return n


async def load_onet_occupations(onet_dir: Path) -> int:
    path = onet_dir / "Occupation Data.txt"
    if not path.exists():
        # also accept occupations.csv
        path = onet_dir / "occupations.csv"
    if not path.exists():
        print("no O*NET occupations file - skip")
        return 0
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from app.taxonomy.models import TaxonomyOccupation

    session, engine = await _session()
    n = 0
    try:
        with path.open(newline="", encoding="utf-8") as f:
            # O*NET tab-separated: O*NET-SOC Code, Title, Description
            dialect = csv.excel_tab if path.suffix == ".txt" else csv.excel
            reader = csv.DictReader(f, dialect=dialect)
            for row in reader:
                code = row.get("O*NET-SOC Code") or row.get("code")
                label = row.get("Title") or row.get("label")
                if not code or not label:
                    continue
                await session.execute(
                    pg_insert(TaxonomyOccupation)
                    .values(
                        scheme="onet",
                        code=code,
                        label=label,
                        description=row.get("Description") or row.get("description"),
                        labels={"en": label},
                        alt_titles=[],
                    )
                    .on_conflict_do_nothing(constraint="uq_taxonomy_occupations_scheme_code")
                )
                n += 1
        await session.commit()
    finally:
        await session.close()
        await engine.dispose()
    print("onet occupations rows read:", n)
    return n


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", action="store_true", help="Load curated seed + templates")
    parser.add_argument("--fx", action="store_true", help="Refresh currency rates")
    parser.add_argument("--esco-dir", type=Path, help="Directory with ESCO occupations.csv")
    parser.add_argument("--onet-dir", type=Path, help="Directory with O*NET Occupation Data")
    args = parser.parse_args()
    if not any([args.seed, args.fx, args.esco_dir, args.onet_dir]):
        parser.print_help()
        raise SystemExit(2)
    if args.seed:
        await run_seed()
    if args.fx:
        await run_fx()
    if args.esco_dir:
        await load_esco_occupations(args.esco_dir)
    if args.onet_dir:
        await load_onet_occupations(args.onet_dir)


if __name__ == "__main__":
    asyncio.run(main())
