"""Company directory writes: add careers page, stats."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select

from app.companies.ats_detect import detect_ats_url
from app.companies.models import Company, CompanyBoard
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.sources.models import Source


async def add_careers_url(ctx: WorkspaceContext, url: str) -> CompanyBoard:
    detected = detect_ats_url(url)
    if detected is None:
        raise AppError("ats_not_detected", "Could not detect an ATS from that URL", 422)
    existing = (
        await ctx.session.execute(
            select(CompanyBoard).where(
                CompanyBoard.ats == detected.ats, CompanyBoard.slug == detected.slug
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    company = Company(
        name=detected.slug.replace("-", " ").title(),
        normalized_name=detected.slug.replace("-", " ").lower(),
        meta={"added_by_workspace": str(ctx.workspace_id)},
    )
    ctx.session.add(company)
    await ctx.session.flush()
    board = CompanyBoard(
        company_id=company.id,
        ats=detected.ats,
        slug=detected.slug,
        url=detected.url,
        status="active",
        poll_tier="warm",
        validated_at=datetime.now(UTC),
        validation_method="user",
    )
    ctx.session.add(board)
    await ctx.session.flush()
    from app.audit import service as audit

    await audit.record(
        ctx,
        action="company_board.added",
        target_type="company_board",
        target_id=str(board.id),
        after={"ats": board.ats, "slug": board.slug},
    )
    return board


async def directory_stats(session) -> dict[str, int]:
    boards = (
        await session.execute(
            select(func.count()).select_from(CompanyBoard).where(CompanyBoard.status == "active")
        )
    ).scalar_one()
    companies = (await session.execute(select(func.count()).select_from(Company))).scalar_one()
    sources = (await session.execute(select(func.count()).select_from(Source))).scalar_one()
    return {
        "boards_active": int(boards),
        "companies": int(companies),
        "sources": int(sources),
    }
