#!/usr/bin/env python3
"""Company board directory refresh.

Usage:
  # Seed ≥5000 validated boards (local / CI)
  uv run python scripts/sources/refresh_directory.py --seed

  # Common Crawl CDX import (batched, resumable): pass a CDX JSONL of ATS URLs
  uv run python scripts/sources/refresh_directory.py --cdx-jsonl /tmp/ats-cdx.jsonl

Never point at prod without the unlock word (no-prod-deploy.mdc).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
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


async def run_seed(target: int) -> None:
    from app.companies.seed import seed_directory

    engine = create_async_engine(_owner_url())
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        stats = await seed_directory(session, target_boards=target)
        await session.commit()
        print(stats)
    await engine.dispose()


async def run_cdx(path: Path, *, limit: int = 10_000) -> None:
    from sqlalchemy import select

    from app.companies.ats_detect import detect_ats_url
    from app.companies.models import Company, CompanyBoard

    engine = create_async_engine(_owner_url())
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    added = 0
    now = datetime.now(UTC)
    async with factory() as session:
        with path.open() as f:
            for line in f:
                if added >= limit:
                    break
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                url = row.get("url") or row.get("original") or ""
                detected = detect_ats_url(url)
                if detected is None:
                    continue
                exists = (
                    await session.execute(
                        select(CompanyBoard).where(
                            CompanyBoard.ats == detected.ats,
                            CompanyBoard.slug == detected.slug,
                        )
                    )
                ).scalar_one_or_none()
                if exists:
                    continue
                company = Company(
                    name=detected.slug.replace("-", " ").title(),
                    normalized_name=detected.slug.replace("-", " ").lower(),
                    meta={"cdx": True},
                )
                session.add(company)
                await session.flush()
                session.add(
                    CompanyBoard(
                        company_id=company.id,
                        ats=detected.ats,
                        slug=detected.slug,
                        url=detected.url,
                        status="active",
                        poll_tier="cold",
                        validated_at=now,
                        validation_method="cdx",
                    )
                )
                added += 1
                if added % 200 == 0:
                    await session.commit()
        await session.commit()
    await engine.dispose()
    print({"added": added})


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", action="store_true")
    p.add_argument("--target", type=int, default=5000)
    p.add_argument("--cdx-jsonl", type=Path)
    p.add_argument("--limit", type=int, default=10_000)
    args = p.parse_args()
    if args.seed:
        asyncio.run(run_seed(args.target))
    elif args.cdx_jsonl:
        asyncio.run(run_cdx(args.cdx_jsonl, limit=args.limit))
    else:
        p.error("pass --seed or --cdx-jsonl")


if __name__ == "__main__":
    main()
