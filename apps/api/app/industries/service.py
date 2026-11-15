"""Workspace industries and the resolved experience manifest."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.industries import models as m
from app.industries.packs.general import GENERAL
from app.industries.registry import (
    BASE_INDUSTRY,
    DEFAULT_WORKSPACE_INDUSTRY,
    get_pack,
    is_known,
    pack_for_template,
)
from app.industries.resolve import resolve_pack, resolve_workspace
from app.industries.schema import IndustryPack
from app.tracks import models as track_models
from app.tracks.criteria import CriteriaV1


async def _rows(db: AsyncSession, workspace_id: uuid.UUID) -> list[m.WorkspaceIndustry]:
    return list(
        (
            await db.execute(
                select(m.WorkspaceIndustry)
                .where(m.WorkspaceIndustry.workspace_id == workspace_id)
                .order_by(m.WorkspaceIndustry.is_primary.desc(), m.WorkspaceIndustry.created_at)
            )
        ).scalars()
    )


def _pack_for_row(row: m.WorkspaceIndustry) -> IndustryPack:
    pack = get_pack(row.industry_key, custom=row.custom_pack)
    return pack or GENERAL


def _primary_key(rows: list[m.WorkspaceIndustry]) -> str:
    for row in rows:
        if row.is_primary:
            return row.industry_key
    return rows[0].industry_key if rows else BASE_INDUSTRY


def _summary(pack: IndustryPack, *, is_primary: bool, custom: bool = False) -> dict[str, Any]:
    return {
        "key": pack.key,
        "label_key": pack.label_key,
        "label": pack.display_name or None,
        "icon": pack.icon,
        "is_primary": is_primary,
        "custom": custom,
    }


async def ensure_industry(
    db: AsyncSession, *, workspace_id: uuid.UUID, industry_key: str, is_primary: bool = True
) -> m.WorkspaceIndustry:
    """Create the initial field row. Runs inside creation's transaction and RLS context."""
    if not is_known(industry_key):
        industry_key = DEFAULT_WORKSPACE_INDUSTRY
    row = m.WorkspaceIndustry(
        workspace_id=workspace_id, industry_key=industry_key, is_primary=is_primary
    )
    db.add(row)
    await db.flush()
    return row


async def enabled_keys(ctx: WorkspaceContext) -> set[str]:
    rows = await _rows(ctx.session, ctx.workspace_id)
    return {row.industry_key for row in rows} | {BASE_INDUSTRY}


async def enabled_packs(ctx: WorkspaceContext) -> list[IndustryPack]:
    rows = await _rows(ctx.session, ctx.workspace_id)
    packs = [_pack_for_row(row) for row in rows]
    return packs or [GENERAL]


async def list_for_workspace(ctx: WorkspaceContext) -> list[dict[str, Any]]:
    rows = await _rows(ctx.session, ctx.workspace_id)
    out: list[dict[str, Any]] = []
    # General is always available and always last; it is not a stored choice.
    for row in rows:
        pack = _pack_for_row(row)
        out.append(_summary(pack, is_primary=row.is_primary, custom=bool(row.custom_pack)))
    if not out:
        out.append(_summary(GENERAL, is_primary=True))
    else:
        out.append(_summary(GENERAL, is_primary=False))
    return out


async def get_experience(ctx: WorkspaceContext) -> dict[str, Any]:
    rows = await _rows(ctx.session, ctx.workspace_id)
    primary = _primary_key(rows)
    enabled: list[IndustryPack] = []
    packs: dict[str, dict[str, Any]] = {}
    for row in rows:
        pack = _pack_for_row(row)
        enabled.append(pack)
        packs[pack.key] = resolve_pack(pack)
    if not enabled:
        enabled.append(GENERAL)
    if BASE_INDUSTRY not in packs:
        packs[BASE_INDUSTRY] = resolve_pack(GENERAL)
    if primary not in packs:
        pack = get_pack(primary) or GENERAL
        if all(existing.key != pack.key for existing in enabled):
            enabled.append(pack)
        packs[pack.key] = resolve_pack(pack)

    manifest = resolve_workspace(enabled, primary_key=primary)
    return {
        "primary": primary,
        "enabled": await list_for_workspace(ctx),
        "manifest": manifest,
        "packs": packs,
    }


async def add_industry(
    ctx: WorkspaceContext, key: str, *, is_primary: bool = False
) -> list[dict[str, Any]]:
    if key == BASE_INDUSTRY:
        raise AppError("general_is_implicit", "General is always available", 422)
    if not is_known(key):
        raise AppError("unknown_industry", "Unknown field of work", 422)
    rows = await _rows(ctx.session, ctx.workspace_id)
    existing = next((row for row in rows if row.industry_key == key), None)
    if existing is not None:
        if is_primary and not existing.is_primary:
            return await set_primary(ctx, key)
        return await list_for_workspace(ctx)
    if not rows:
        is_primary = True
    if is_primary:
        await ctx.session.execute(
            update(m.WorkspaceIndustry)
            .where(m.WorkspaceIndustry.workspace_id == ctx.workspace_id)
            .values(is_primary=False)
        )
    ctx.session.add(
        m.WorkspaceIndustry(workspace_id=ctx.workspace_id, industry_key=key, is_primary=is_primary)
    )
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="workspace.industry_added",
        target_type="workspace",
        target_id=str(ctx.workspace_id),
        after={"industry": key, "is_primary": is_primary},
    )
    return await list_for_workspace(ctx)


async def remove_industry(ctx: WorkspaceContext, key: str) -> list[dict[str, Any]]:
    if key == BASE_INDUSTRY:
        raise AppError("general_is_implicit", "General is always available", 422)
    rows = await _rows(ctx.session, ctx.workspace_id)
    target = next((row for row in rows if row.industry_key == key), None)
    if target is None:
        raise AppError("not_found", "Field of work not found", 404)

    fallback = BASE_INDUSTRY
    was_primary = target.is_primary
    await ctx.session.delete(target)
    await ctx.session.flush()
    if was_primary:
        for row in rows:
            if row.industry_key == key:
                continue
            row.is_primary = True
            fallback = row.industry_key
            break
        await ctx.session.flush()

    moved = (
        await ctx.session.execute(
            update(track_models.Track)
            .where(
                track_models.Track.workspace_id == ctx.workspace_id,
                track_models.Track.industry == key,
            )
            .values(industry=fallback)
        )
    ).rowcount  # type: ignore[attr-defined]
    if moved:
        await audit.record(
            ctx,
            action="track.industry_changed",
            target_type="track",
            target_id=None,
            after={"count": int(moved), "from": key, "to": fallback},
        )
    await audit.record(
        ctx,
        action="workspace.industry_removed",
        target_type="workspace",
        target_id=str(ctx.workspace_id),
        before={"industry": key, "is_primary": was_primary},
        after={"tracks_moved": int(moved or 0), "fallback": fallback},
    )
    return await list_for_workspace(ctx)


async def set_primary(ctx: WorkspaceContext, key: str) -> list[dict[str, Any]]:
    rows = await _rows(ctx.session, ctx.workspace_id)
    target = next((row for row in rows if row.industry_key == key), None)
    if target is None:
        raise AppError("not_found", "Field of work not found", 404)
    if target.is_primary:
        return await list_for_workspace(ctx)
    before = _primary_key(rows)
    for row in rows:
        row.is_primary = False
    await ctx.session.flush()
    target.is_primary = True
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="workspace.industry_primary_changed",
        target_type="workspace",
        target_id=str(ctx.workspace_id),
        before={"industry": before},
        after={"industry": key},
    )
    return await list_for_workspace(ctx)


async def industry_for_track(
    ctx: WorkspaceContext,
    *,
    requested: str | None,
    template_slug: str | None = None,
    template_industry: str | None = None,
) -> str:
    if requested:
        if requested == BASE_INDUSTRY:
            return requested
        if requested not in await enabled_keys(ctx):
            raise AppError(
                "unknown_industry",
                "That field of work is not enabled for this workspace",
                422,
            )
        return requested
    if template_slug:
        candidate = pack_for_template(template_industry)
        if candidate == BASE_INDUSTRY or candidate in await enabled_keys(ctx):
            return candidate
        return BASE_INDUSTRY
    rows = await _rows(ctx.session, ctx.workspace_id)
    primary = _primary_key(rows)
    return primary if primary != BASE_INDUSTRY else BASE_INDUSTRY


async def validate_facets(ctx: WorkspaceContext, criteria: CriteriaV1, industry: str) -> None:
    if not criteria.facets:
        return
    rows = await _rows(ctx.session, ctx.workspace_id)
    row = next((r for r in rows if r.industry_key == industry), None)
    pack = _pack_for_row(row) if row is not None else (get_pack(industry) or GENERAL)
    allowed = {facet.key: facet for facet in pack.facets}
    for key, value in criteria.facets.items():
        facet = allowed.get(key)
        if facet is None:
            raise AppError("unknown_facet", f"Unknown filter for this search: {key}", 422)
        if facet.kind in ("multi", "single"):
            options = {option.key for option in facet.options}
            values = value if isinstance(value, list) else [str(value)]
            unknown = [item for item in values if item not in options]
            if unknown:
                raise AppError(
                    "unknown_facet_option",
                    f"Unknown option for {key}: {unknown[0]}",
                    422,
                )


async def add_custom_industry(
    ctx: WorkspaceContext,
    *,
    key: str,
    description: str,
    base_pack: str | None = None,
    is_primary: bool = False,
) -> list[dict[str, Any]]:
    from app.industries.detect import draft_custom_pack
    from app.industries.schema import IndustryPack

    draft = draft_custom_pack(description, base_pack=base_pack)
    pack = IndustryPack.model_validate(draft["pack"])
    pack_data = pack.model_dump(mode="json")
    if pack.key != key:
        raise AppError(
            "draft_changed",
            "That description no longer matches the draft. Draft the field again.",
            409,
        )
    rows = await _rows(ctx.session, ctx.workspace_id)
    existing = next((row for row in rows if row.industry_key == key), None)
    if existing is not None:
        if existing.custom_pack is None:
            raise AppError("conflict", "That field already exists", 409)
        existing.custom_pack = pack_data
        await ctx.session.flush()
        if is_primary:
            await set_primary(ctx, key)
    else:
        if is_primary:
            for row in rows:
                row.is_primary = False
            await ctx.session.flush()
        ctx.session.add(
            m.WorkspaceIndustry(
                workspace_id=ctx.workspace_id,
                industry_key=key,
                is_primary=is_primary or not rows,
                custom_pack=pack_data,
            )
        )
        await ctx.session.flush()
    await audit.record(
        ctx,
        action="workspace.custom_pack_accepted",
        target_type="workspace",
        target_id=str(ctx.workspace_id),
        after={"industry": key, "base": pack.sources.adapters[:3]},
    )
    return await list_for_workspace(ctx)


async def pack_for_track(
    session: AsyncSession, *, workspace_id: uuid.UUID, industry: str
) -> IndustryPack:
    """Resolve a curated pack or an accepted custom pack for a Track."""
    known = get_pack(industry)
    if known is not None:
        return known
    row = (
        await session.execute(
            select(m.WorkspaceIndustry).where(
                m.WorkspaceIndustry.workspace_id == workspace_id,
                m.WorkspaceIndustry.industry_key == industry,
            )
        )
    ).scalar_one_or_none()
    if row is not None and row.custom_pack:
        return get_pack(industry, custom=row.custom_pack) or GENERAL
    return GENERAL
