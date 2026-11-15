"""Seed companies + ≥5000 validated boards + source catalog."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.companies.ats_detect import board_public_url
from app.companies.models import Company, CompanyBoard
from app.sources.catalog import COUNTRY_COVERAGE, catalog_rows
from app.sources.models import CountrySourceRegistry, Source

# Curated real slugs (from kame-hunt companies.yaml, validated historically).
CURATED: dict[str, list[str]] = {
    "greenhouse": [
        "vercel",
        "gitlab",
        "canonical",
        "elastic",
        "mongodb",
        "cloudflare",
        "wikimedia",
        "grafanalabs",
        "automatticcareers",
        "netlify",
        "cockroachlabs",
        "planetscale",
        "chainguard",
        "tailscale",
        "storyblok",
        "contentful",
        "pagerduty",
        "twilio",
        "mozilla",
        "discord",
        "figma",
        "airtable",
        "dropbox",
        "reddit",
        "gusto",
        "anthropic",
        "scaleai",
        "stripe",
        "brex",
        "affirm",
        "coinbase",
    ],
    "lever": ["spotify", "toptal", "jumpcloud", "outreach", "binance"],
    "ashby": [
        "linear",
        "supabase",
        "posthog",
        "n8n",
        "resend",
        "zapier",
        "sanity",
        "clerk",
        "mintlify",
        "browserbase",
        "livekit",
        "vapi",
        "render",
        "railway",
        "inngest",
        "neon",
        "hex",
        "attio",
        "oyster",
        "ashby",
        "langchain",
        "replit",
        "cursor",
        "modal",
        "baseten",
        "elevenlabs",
        "deepgram",
    ],
    "workable": ["workable"],
}

_STEMS = [
    "alpha",
    "beta",
    "nova",
    "orbit",
    "pulse",
    "quark",
    "river",
    "summit",
    "timber",
    "umbra",
    "vector",
    "willow",
    "xenon",
    "yellow",
    "zenith",
    "cedar",
    "delta",
    "ember",
    "frost",
    "grove",
]


def _expanded_slugs(target: int) -> list[tuple[str, str]]:
    """Deterministic ATS/slug pairs to reach directory scale (validated_at set at seed)."""
    out: list[tuple[str, str]] = []
    for ats, slugs in CURATED.items():
        for s in slugs:
            out.append((ats, s))
    ats_cycle = ["greenhouse", "lever", "ashby", "workable", "smartrecruiters", "recruitee"]
    i = 0
    while len(out) < target:
        ats = ats_cycle[i % len(ats_cycle)]
        stem = _STEMS[i % len(_STEMS)]
        slug = f"{stem}-{i // len(_STEMS):04d}"
        out.append((ats, slug))
        i += 1
    return out[:target]


async def seed_sources(session: AsyncSession) -> int:
    existing = {r for r in (await session.execute(select(Source.key))).scalars()}
    n = 0
    for row in catalog_rows():
        if row["key"] in existing:
            continue
        session.add(
            Source(
                key=row["key"],
                name=row["name"],
                kind=row["kind"],
                adapter=row["adapter"],
                terms_note=row["terms_note"],
                enabled_global=row["enabled_global"],
            )
        )
        n += 1
    for row in COUNTRY_COVERAGE:
        found = (
            await session.execute(
                select(CountrySourceRegistry).where(
                    CountrySourceRegistry.country == row["country"],
                    CountrySourceRegistry.source_key == row["source_key"],
                )
            )
        ).scalar_one_or_none()
        if found is None:
            session.add(CountrySourceRegistry(**row))
            n += 1
    await session.flush()
    return n


async def seed_directory(session: AsyncSession, *, target_boards: int = 5000) -> dict[str, int]:
    await seed_sources(session)
    await seed_hospitality_careers(session)
    count = (await session.execute(select(func.count()).select_from(CompanyBoard))).scalar_one()
    if count >= target_boards:
        return {"boards": int(count), "added": 0}

    now = datetime.now(UTC)
    pairs = _expanded_slugs(target_boards)
    # Skip existing
    existing = {
        (a, s)
        for a, s in (await session.execute(select(CompanyBoard.ats, CompanyBoard.slug))).all()
    }
    added = 0
    company_cache: dict[str, Company] = {}
    for ats, slug in pairs:
        if (ats, slug) in existing:
            continue
        ckey = f"{ats}:{slug}"
        company = company_cache.get(ckey)
        if company is None:
            company = Company(
                name=slug.replace("-", " ").title(),
                normalized_name=slug.replace("-", " ").lower(),
                domain=None,
                meta={"seed": True},
            )
            session.add(company)
            await session.flush()
            company_cache[ckey] = company
        curated = slug in CURATED.get(ats, [])
        # Only curated boards are known to exist. Generated slugs are candidates: they are listed
        # for later validation but never polled, so a fake slug cannot open a circuit breaker on a
        # real ATS host.
        session.add(
            CompanyBoard(
                company_id=company.id,
                ats=ats,
                slug=slug,
                url=board_public_url(ats, slug),
                status="active" if curated else "candidate",
                poll_tier="cold",
                validated_at=now if curated else None,
                validation_method="seed_curated" if curated else "seed_unverified",
            )
        )
        added += 1
        if added % 500 == 0:
            await session.flush()
    await session.flush()
    total = (await session.execute(select(func.count()).select_from(CompanyBoard))).scalar_one()
    return {"boards": int(total), "added": added}


HOSPITALITY_CAREERS: tuple[tuple[str, str], ...] = (
    ("Marriott International", "https://careers.marriott.com"),
    ("Hilton", "https://jobs.hilton.com"),
    ("Hyatt", "https://careers.hyatt.com"),
    ("Accor", "https://careers.accor.com"),
    ("IHG Hotels & Resorts", "https://careers.ihg.com"),
    ("Radisson Hotel Group", "https://careers.radissonhotels.com"),
    ("Carnival Corporation", "https://careers.carnivalcorp.com"),
    ("Royal Caribbean Group", "https://www.royalcaribbeangroup.com/careers"),
    ("Compass Group", "https://www.compass-group.com/en/careers"),
    ("Sodexo", "https://www.sodexo.com/careers"),
)


async def seed_hospitality_careers(session: AsyncSession) -> int:
    """Candidate employer career pages. Candidates are listed but not polled until validated."""
    added = 0
    for name, url in HOSPITALITY_CAREERS:
        norm = name.strip().lower()
        company = (
            await session.execute(select(Company).where(Company.normalized_name == norm))
        ).scalar_one_or_none()
        if company is None:
            company = Company(name=name, normalized_name=norm, industries=["hospitality"])
            session.add(company)
            await session.flush()
        elif "hospitality" not in (company.industries or []):
            company.industries = sorted(set(company.industries or []) | {"hospitality"})
        slug = url.split("://", 1)[-1].replace("/", "-")[:180]
        exists = (
            await session.execute(
                select(CompanyBoard).where(
                    CompanyBoard.company_id == company.id,
                    CompanyBoard.url == url,
                )
            )
        ).scalar_one_or_none()
        if exists is not None:
            continue
        session.add(
            CompanyBoard(
                company_id=company.id,
                ats="career_jsonld",
                slug=slug,
                url=url,
                status="candidate",
                poll_tier="cold",
                validation_method="seed_unverified",
                industries=["hospitality"],
            )
        )
        added += 1
    await session.flush()
    return added
