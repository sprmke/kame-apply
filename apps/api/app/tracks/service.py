"""Track CRUD, criteria updates, duplicate/archive/reorder."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal, cast

from sqlalchemy import select

from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.profiles import models as profile_models
from app.taxonomy import models as tax_models
from app.tracks import models as m
from app.tracks.compile_filter import compile_filter
from app.tracks.compile_nl import compile_text
from app.tracks.criteria import criteria_from_dict, empty_criteria
from app.tracks.currency import normalize_salary
from app.tracks.diff import diff_criteria
from app.tracks.geocode import geocode_place
from app.tracks.schemas import CriteriaPut, TrackCreate, TrackUpdate
from app.tracks.summary import summarize
from app.tracks.validate import validate_criteria

PREVIEW_MESSAGE = "Preview available after first discovery"


def _hue(n: int) -> int:
    return max(1, min(8, int(n)))


async def _get_profile(
    ctx: WorkspaceContext, profile_id: uuid.UUID
) -> profile_models.CandidateProfile:
    row = await ctx.session.get(profile_models.CandidateProfile, profile_id)
    if row is None or row.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Profile not found", 404)
    return row


async def _get_track(ctx: WorkspaceContext, track_id: uuid.UUID) -> m.Track:
    row = await ctx.session.get(m.Track, track_id)
    if row is None or row.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track not found", 404)
    return row


async def _get_criteria(ctx: WorkspaceContext, track_id: uuid.UUID) -> m.TrackCriteria:
    row = (
        await ctx.session.execute(
            select(m.TrackCriteria).where(m.TrackCriteria.track_id == track_id)
        )
    ).scalar_one_or_none()
    if row is None or row.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track criteria not found", 404)
    return row


def _criteria_read(track: m.Track, crit: m.TrackCriteria) -> dict[str, Any]:
    structured = criteria_from_dict(crit.structured)
    return {
        "nl_text": crit.nl_text,
        "structured": crit.structured,
        "compiled": crit.compiled,
        "version": crit.version,
        "summary": track.summary or summarize(structured),
        "warnings": validate_criteria(structured),
    }


async def list_tracks(ctx: WorkspaceContext, *, include_archived: bool = False) -> list[m.Track]:
    q = select(m.Track).order_by(m.Track.sort_order, m.Track.created_at)
    if not include_archived:
        q = q.where(m.Track.status.in_(("active", "paused")))
    return list((await ctx.session.execute(q)).scalars())


async def get_detail(ctx: WorkspaceContext, track_id: uuid.UUID) -> dict[str, Any]:
    track = await _get_track(ctx, track_id)
    crit = await _get_criteria(ctx, track_id)
    return {"track": track, "criteria": _criteria_read(track, crit)}


async def create_track(ctx: WorkspaceContext, body: TrackCreate) -> dict[str, Any]:
    await _get_profile(ctx, body.profile_id)
    criteria = body.criteria or empty_criteria()
    nl_text = body.nl_text or ""
    template_slug = body.template_slug

    if template_slug:
        tmpl = (
            await ctx.session.execute(
                select(tax_models.TrackTemplate).where(
                    tax_models.TrackTemplate.slug == template_slug
                )
            )
        ).scalar_one_or_none()
        if tmpl is None:
            raise AppError("template_not_found", "Template not found", 404)
        if body.criteria is None:
            criteria = criteria_from_dict(tmpl.criteria)
        if not nl_text:
            nl_text = tmpl.nl_seed
        name = body.name or tmpl.name
        icon = body.icon if body.icon != "ph:path" else tmpl.icon
        hue = body.color_hue if body.color_hue != 1 else tmpl.color_hue
    else:
        if not body.name:
            raise AppError("name_required", "Name is required", 422)
        name = body.name
        icon = body.icon
        hue = body.color_hue

    criteria = normalize_salary(criteria)
    if not criteria.has_role_signal() and not nl_text.strip():
        raise AppError(
            "missing_role",
            "Add a title, occupation, or description before saving",
            422,
        )

    max_sort = (
        await ctx.session.execute(
            select(m.Track.sort_order)
            .where(m.Track.status == "active")
            .order_by(m.Track.sort_order.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    sort_order = (max_sort or 0) + 1

    track = m.Track(
        workspace_id=ctx.workspace_id,
        profile_id=body.profile_id,
        name=name,
        icon=icon,
        color_hue=_hue(hue),
        autonomy=body.autonomy,
        sort_order=sort_order,
        summary=summarize(criteria),
        template_slug=template_slug,
        created_by=ctx.user_id,
    )
    ctx.session.add(track)
    await ctx.session.flush()

    crit = m.TrackCriteria(
        workspace_id=ctx.workspace_id,
        track_id=track.id,
        nl_text=nl_text,
        structured=criteria.model_dump_stored(),
        compiled=compile_filter(criteria),
        version=1,
    )
    ctx.session.add(crit)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="track.created",
        target_type="track",
        target_id=str(track.id),
        after={
            "name": track.name,
            "profile_id": str(track.profile_id),
            "template_slug": template_slug,
            "criteria_version": 1,
        },
    )
    await ctx.session.refresh(track)
    await ctx.session.refresh(crit)
    return {"track": track, "criteria": _criteria_read(track, crit)}


async def update_track(ctx: WorkspaceContext, track_id: uuid.UUID, body: TrackUpdate) -> m.Track:
    track = await _get_track(ctx, track_id)
    before = {"name": track.name, "autonomy": track.autonomy, "color_hue": track.color_hue}
    data = body.model_dump(exclude_unset=True)
    if "color_hue" in data and data["color_hue"] is not None:
        data["color_hue"] = _hue(data["color_hue"])
    for k, v in data.items():
        setattr(track, k, v)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="track.updated",
        target_type="track",
        target_id=str(track.id),
        before=before,
        after={k: getattr(track, k) for k in before},
    )
    await ctx.session.refresh(track)
    return track


async def put_criteria(
    ctx: WorkspaceContext, track_id: uuid.UUID, body: CriteriaPut
) -> dict[str, Any]:
    track = await _get_track(ctx, track_id)
    crit = await _get_criteria(ctx, track_id)
    before_ver = crit.version
    criteria = normalize_salary(body.criteria)
    if not criteria.has_role_signal():
        raise AppError("missing_role", "Add at least one title or occupation", 422)

    # Geocode locations missing coords (cache only; network optional).
    new_locs = []
    for loc in criteria.locations:
        if loc.lat is None or loc.lon is None:
            hit = await geocode_place(ctx.session, loc.place, allow_network=False)
            if hit is not None:
                loc = loc.model_copy(
                    update={"lat": hit.lat, "lon": hit.lon, "country": hit.country or loc.country}
                )
        new_locs.append(loc)
    criteria = criteria.model_copy(update={"locations": new_locs})

    old = criteria_from_dict(crit.structured)
    crit.structured = criteria.model_dump_stored()
    crit.compiled = compile_filter(criteria)
    crit.version = before_ver + 1
    if body.nl_text is not None:
        crit.nl_text = body.nl_text
    track.summary = summarize(criteria)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="track.criteria_updated",
        target_type="track",
        target_id=str(track.id),
        before={"version": before_ver},
        after={
            "version": crit.version,
            "diff_count": len(diff_criteria(old, criteria)),
        },
    )
    # Phase 6: re-rank when criteria change (no LLM inline).
    try:
        from app.matching.service import score_track_jobs

        await score_track_jobs(ctx, track_id, llm_top_n=0)
    except Exception as exc:
        import structlog

        structlog.get_logger().warning("score_after_criteria_failed", error=str(exc)[:200])
    await ctx.session.refresh(track)
    await ctx.session.refresh(crit)
    return {"track": track, "criteria": _criteria_read(track, crit)}


async def compile_and_maybe_apply(
    ctx: WorkspaceContext,
    settings,
    track_id: uuid.UUID,
    *,
    text: str,
    apply: bool,
    run_structured=None,
    model_factory=None,
) -> dict[str, Any]:
    await _get_track(ctx, track_id)
    crit = await _get_criteria(ctx, track_id)
    current = criteria_from_dict(crit.structured)
    compiled = await compile_text(
        ctx,
        settings,
        text=text,
        current=current,
        run_structured=run_structured,
        model_factory=model_factory,
    )
    if not apply:
        return compiled

    body = CriteriaPut(criteria=compiled["criteria"], nl_text=text)
    detail = await put_criteria(ctx, track_id, body)
    return {**compiled, "track": detail["track"], "applied": True}


async def duplicate_track(ctx: WorkspaceContext, track_id: uuid.UUID) -> dict[str, Any]:
    src = await _get_track(ctx, track_id)
    src_crit = await _get_criteria(ctx, track_id)
    autonomy = cast(
        Literal["discover", "prepare", "assist", "auto_submit"],
        "assist" if src.autonomy == "auto_submit" else src.autonomy,
    )
    body = TrackCreate(
        profile_id=src.profile_id,
        name=f"{src.name} copy",
        icon=src.icon,
        color_hue=src.color_hue,
        autonomy=autonomy,
        nl_text=src_crit.nl_text,
        criteria=criteria_from_dict(src_crit.structured),
    )
    created = await create_track(ctx, body)
    await audit.record(
        ctx,
        action="track.duplicated",
        target_type="track",
        target_id=str(created["track"].id),
        after={"source_id": str(src.id)},
    )
    return created


async def archive_track(ctx: WorkspaceContext, track_id: uuid.UUID) -> m.Track:
    track = await _get_track(ctx, track_id)
    if track.status == "archived":
        return track
    track.status = "archived"
    track.archived_at = datetime.now(UTC)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="track.archived",
        target_type="track",
        target_id=str(track.id),
        after={"name": track.name},
    )
    await ctx.session.refresh(track)
    return track


async def reorder_tracks(ctx: WorkspaceContext, ordered_ids: list[uuid.UUID]) -> list[m.Track]:
    rows = await list_tracks(ctx, include_archived=False)
    by_id = {r.id: r for r in rows}
    if set(ordered_ids) != set(by_id):
        raise AppError(
            "reorder_mismatch",
            "ordered_ids must list every active Track exactly once",
            422,
        )
    for i, tid in enumerate(ordered_ids):
        by_id[tid].sort_order = i + 1
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="track.reordered",
        target_type="track",
        target_id=None,
        after={"count": len(ordered_ids)},
    )
    return await list_tracks(ctx, include_archived=False)


async def list_templates(ctx: WorkspaceContext) -> list[tax_models.TrackTemplate]:
    # ctx ensures auth; templates are global.
    return list(
        (
            await ctx.session.execute(
                select(tax_models.TrackTemplate).order_by(
                    tax_models.TrackTemplate.sort_order, tax_models.TrackTemplate.name
                )
            )
        ).scalars()
    )


async def geocode(ctx: WorkspaceContext, place: str, *, allow_network: bool = True):
    return await geocode_place(ctx.session, place, allow_network=allow_network)
