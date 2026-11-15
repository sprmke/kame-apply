"""discover_track: pull sources → ingest → interim rule-based Track link."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit
from app.companies.models import CompanyBoard
from app.core.errors import AppError
from app.core.rls import set_request_context
from app.core.security import WorkspaceContext
from app.industries import service as industries_service
from app.industries.schema import IndustryPack
from app.jobs.ingest import mark_missed_jobs, upsert_raw_job
from app.jobs.link import rule_match
from app.jobs.models import DiscoveryRun, TrackJob
from app.sources.models import Source, TrackSource
from app.tracks import models as track_models
from kame_core.sources import get_adapter
from kame_core.sources.http import BlockSignalError, fetch_json

logger = logging.getLogger(__name__)


def _enabled_source_keys(
    track_sources: list[tuple[TrackSource, Source]], allowed: set[str]
) -> set[str]:
    """Enabled track sources that the field pack can actually use."""
    return {
        source.key
        for _, source in track_sources
        if source.enabled_global and not source.circuit_open and source.key in allowed
    }


async def _boards_for_run(
    session: AsyncSession, *, limit: int = 8, pack: IndustryPack | None = None
) -> list[CompanyBoard]:
    """Pick boards for the Track's field. Empty-industry boards stay eligible (user-added pages)."""
    from sqlalchemy import or_

    tags = list(pack.sources.employer_tags) if pack is not None else []
    q = select(CompanyBoard).where(
        CompanyBoard.status == "active",
        CompanyBoard.validation_method.in_(("seed_curated", "api", "user")),
    )
    if tags:
        q = q.where(
            or_(
                CompanyBoard.industries.overlap(tags),
                CompanyBoard.industries == [],
            )
        )
    rows = (
        (await session.execute(q.order_by(CompanyBoard.poll_tier.asc()).limit(limit)))
        .scalars()
        .all()
    )
    if rows:
        return list(rows)
    fallback = select(CompanyBoard).where(CompanyBoard.status == "active")
    if tags:
        fallback = fallback.where(
            or_(CompanyBoard.industries.overlap(tags), CompanyBoard.industries == [])
        )
    return list((await session.execute(fallback.limit(limit))).scalars().all())


async def run_discover_track(
    ctx: WorkspaceContext,
    track_id: uuid.UUID,
    *,
    run_id: uuid.UUID | None = None,
    fixture_root: Path | None = None,
    board_limit: int = 6,
    commit_progress: bool = False,
) -> DiscoveryRun:
    track = await ctx.session.get(track_models.Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track not found", 404)
    crit = (
        await ctx.session.execute(
            select(track_models.TrackCriteria).where(
                track_models.TrackCriteria.track_id == track_id
            )
        )
    ).scalar_one()
    pack = await industries_service.pack_for_track(
        ctx.session, workspace_id=ctx.workspace_id, industry=track.industry
    )

    run = None
    if run_id:
        run = await ctx.session.get(DiscoveryRun, run_id)
    if run is None:
        run = DiscoveryRun(
            workspace_id=ctx.workspace_id,
            track_id=track_id,
            status="running",
            trigger="manual",
            started_at=datetime.now(UTC),
            progress={"boards_checked": 0, "jobs_found": 0, "jobs_new": 0, "linked": 0},
        )
        ctx.session.add(run)
        await ctx.session.flush()
    else:
        run.status = "running"
        run.started_at = datetime.now(UTC)
        run.progress = {"boards_checked": 0, "jobs_found": 0, "jobs_new": 0, "linked": 0}

    progress = dict(run.progress or {})
    linked_before = int(
        (
            await ctx.session.execute(
                select(func.count()).select_from(TrackJob).where(TrackJob.track_id == track_id)
            )
        ).scalar_one()
    )

    async def publish_progress() -> None:
        """Flush progress; in the background path commit so pollers see counts mid-run."""
        run.progress = progress
        await ctx.session.flush()
        if commit_progress:
            await ctx.session.commit()
            await set_request_context(
                ctx.session,
                user_id=str(ctx.user_id) if ctx.user_id else None,
                workspace_id=str(ctx.workspace_id),
            )

    try:
        # Board sources enabled for track (or defaults)
        track_sources = (
            await ctx.session.execute(
                select(TrackSource, Source)
                .join(Source)
                .where(TrackSource.track_id == track_id, TrackSource.enabled.is_(True))
            )
        ).all()
        allowed = set(pack.sources.adapters)
        # A track created before pack-scoped defaults may still carry older source rows. Keep
        # only sources this field can use, so a hospitality track never polls tech boards.
        adapter_keys = _enabled_source_keys(track_sources, allowed)
        if not adapter_keys:
            adapter_keys = {
                s.key
                for s in (
                    await ctx.session.execute(
                        select(Source).where(
                            Source.enabled_global.is_(True),
                            Source.circuit_open.is_(False),
                            Source.kind.in_(("ats", "board", "search", "career_page")),
                        )
                    )
                ).scalars()
                if s.key in allowed
            }

        boards = await _boards_for_run(ctx.session, limit=board_limit, pack=pack)
        for board in boards:
            if board.ats not in adapter_keys:
                continue
            source = (
                await ctx.session.execute(select(Source).where(Source.key == board.ats))
            ).scalar_one_or_none()
            if source is None or not source.enabled_global or source.circuit_open:
                continue
            t0 = time.perf_counter()
            try:
                kwargs: dict[str, Any] = {}
                if fixture_root is not None:
                    fd = fixture_root / board.ats
                    if fd.is_dir():
                        kwargs["fixture_dir"] = fd
                if board.ats == "career_jsonld" and fixture_root is None:
                    # Cheap conditional HEAD for HTML career pages; skip the fetch when unchanged.
                    _, cond_headers, cond_status = await fetch_json(
                        board.url,
                        method="HEAD",
                        etag=board.etag,
                        last_modified=board.last_modified,
                    )
                    if cond_status == 304:
                        board.last_polled_at = datetime.now(UTC)
                        progress["not_modified"] = int(progress.get("not_modified") or 0) + 1
                        progress["boards_checked"] = int(progress.get("boards_checked") or 0) + 1
                        await publish_progress()
                        continue
                    if cond_headers.get("etag"):
                        board.etag = cond_headers["etag"][:255]
                    if cond_headers.get("last-modified"):
                        board.last_modified = cond_headers["last-modified"][:255]
                adapter = get_adapter(board.ats, **kwargs)
                seen: set[str] = set()
                async for raw in adapter.discover({"slug": board.slug}):
                    seen.add(raw.external_id)
                    try:
                        # A savepoint isolates one bad record; a full rollback would discard the
                        # run row and every job already ingested in this run.
                        async with ctx.session.begin_nested():
                            job, created = await upsert_raw_job(ctx.session, raw, board_id=board.id)
                    except Exception:
                        progress["skipped"] = int(progress.get("skipped") or 0) + 1
                        continue
                    progress["jobs_found"] = int(progress.get("jobs_found") or 0) + 1
                    if created:
                        progress["jobs_new"] = int(progress.get("jobs_new") or 0) + 1
                    if rule_match(job, crit.structured):
                        existing = (
                            await ctx.session.execute(
                                select(TrackJob).where(
                                    TrackJob.track_id == track_id, TrackJob.job_id == job.id
                                )
                            )
                        ).scalar_one_or_none()
                        if existing is None:
                            ctx.session.add(
                                TrackJob(
                                    workspace_id=ctx.workspace_id,
                                    track_id=track_id,
                                    job_id=job.id,
                                    status="new",
                                    score=0.5,
                                    fit={"method": "rule_v1"},
                                )
                            )
                            progress["linked"] = int(progress.get("linked") or 0) + 1
                closed = await mark_missed_jobs(
                    ctx.session, source_id=source.id, board_id=board.id, seen_external_ids=seen
                )
                progress["closed"] = int(progress.get("closed") or 0) + closed
                latency = (time.perf_counter() - t0) * 1000
                source.last_success_at = datetime.now(UTC)
                source.success_count = (source.success_count or 0) + 1
                source.avg_latency_ms = (
                    latency
                    if source.avg_latency_ms is None
                    else (source.avg_latency_ms * 0.8 + latency * 0.2)
                )
                board.last_polled_at = datetime.now(UTC)
            except BlockSignalError as exc:
                # One blocked board must not disable every board on that ATS host.
                board.status = "inactive"
                board.meta = {
                    **(board.meta or {}),
                    "blocked": str(exc)[:300],
                    "blocked_at": datetime.now(UTC).isoformat(),
                }
                source.block_signals = (source.block_signals or 0) + 1
                logger.warning("board_blocked ats=%s slug=%s", board.ats, board.slug)
            except Exception as exc:
                source.last_error = str(exc)[:500]
                source.last_error_at = datetime.now(UTC)
                source.error_count = (source.error_count or 0) + 1
            progress["boards_checked"] = int(progress.get("boards_checked") or 0) + 1
            await publish_progress()

        # Layer-2 boards without slug (remotive etc.) once per run
        feed_keys = [
            key
            for key in ("remotive", "remoteok", "arbeitnow", "jobicy", "muse", "himalayas")
            if key in adapter_keys and key in pack.sources.adapters
        ]
        for key in feed_keys:
            if key.startswith("search_"):
                continue
            source = (
                await ctx.session.execute(select(Source).where(Source.key == key))
            ).scalar_one_or_none()
            if source is None or source.circuit_open:
                continue
            try:
                kwargs = {}
                if fixture_root is not None and (fixture_root / key).is_dir():
                    kwargs["fixture_dir"] = fixture_root / key
                adapter = get_adapter(key, **kwargs)
                feed_seen: set[str] = set()
                async for raw in adapter.discover({}):
                    try:
                        async with ctx.session.begin_nested():
                            job, created = await upsert_raw_job(ctx.session, raw)
                    except Exception:
                        progress["skipped"] = int(progress.get("skipped") or 0) + 1
                        continue
                    feed_seen.add(raw.external_id)
                    progress["jobs_found"] = int(progress.get("jobs_found") or 0) + 1
                    if created:
                        progress["jobs_new"] = int(progress.get("jobs_new") or 0) + 1
                    if rule_match(job, crit.structured):
                        existing = (
                            await ctx.session.execute(
                                select(TrackJob).where(
                                    TrackJob.track_id == track_id, TrackJob.job_id == job.id
                                )
                            )
                        ).scalar_one_or_none()
                        if existing is None:
                            ctx.session.add(
                                TrackJob(
                                    workspace_id=ctx.workspace_id,
                                    track_id=track_id,
                                    job_id=job.id,
                                    status="new",
                                    score=0.5,
                                    fit={"method": "rule_v1"},
                                )
                            )
                            progress["linked"] = int(progress.get("linked") or 0) + 1
                # A feed that stops listing a job is the only signal it closed.
                closed = await mark_missed_jobs(
                    ctx.session,
                    source_id=source.id,
                    board_id=None,
                    seen_external_ids=feed_seen,
                )
                if closed:
                    progress["closed"] = int(progress.get("closed") or 0) + closed
                source.last_success_at = datetime.now(UTC)
                source.success_count = (source.success_count or 0) + 1
            except BlockSignalError as exc:
                source.circuit_open = True
                source.block_signals = (source.block_signals or 0) + 1
                source.last_error = str(exc)
                source.last_error_at = datetime.now(UTC)
            except Exception as exc:
                source.last_error = str(exc)[:500]
                source.last_error_at = datetime.now(UTC)
                source.error_count = (source.error_count or 0) + 1
            progress["boards_checked"] = int(progress.get("boards_checked") or 0) + 1
            await publish_progress()

        # Layer 4: keyword + location search for fields those boards do not cover.
        from app.core.config import get_settings
        from app.sources.search_service import run_search_sources

        await run_search_sources(
            ctx,
            track=track,
            run=run,
            progress=progress,
            fixture_root=fixture_root,
            settings=get_settings(),
        )
        await publish_progress()

        # Phase 6: rank linked jobs for this Track
        try:
            from app.matching.service import score_track_jobs

            score_stats = await score_track_jobs(ctx, track_id, llm_top_n=0)
            progress["scored"] = score_stats.get("scored", 0)
            progress["eligible"] = score_stats.get("eligible", 0)
        except Exception as score_exc:
            progress["score_error"] = str(score_exc)[:200]

        linked_after = int(
            (
                await ctx.session.execute(
                    select(func.count()).select_from(TrackJob).where(TrackJob.track_id == track_id)
                )
            ).scalar_one()
        )
        progress["linked"] = max(int(progress.get("linked") or 0), linked_after - linked_before)
        run.status = "succeeded"
        run.finished_at = datetime.now(UTC)
        run.progress = progress
        await audit.record(
            ctx,
            action="discovery.run_completed",
            target_type="discovery_run",
            target_id=str(run.id),
            after=progress,
        )
        await ctx.session.flush()
        return run
    except Exception as exc:
        # Persist the failure instead of re-raising: a raise would roll back the request
        # transaction and erase the run row, so failures would be invisible to the UI and ops.
        run.status = "failed"
        run.error = str(exc)[:1000]
        run.finished_at = datetime.now(UTC)
        run.progress = progress
        await ctx.session.flush()
        logger.exception("discovery_failed run=%s", run.id)
        return run
