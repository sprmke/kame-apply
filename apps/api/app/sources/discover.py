"""discover_track: pull sources → ingest → interim rule-based Track link."""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit
from app.companies.models import CompanyBoard
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.jobs.ingest import mark_missed_jobs, upsert_raw_job
from app.jobs.models import DiscoveryRun, Job, TrackJob
from app.jobs.normalize import normalize_title
from app.sources.models import Source, TrackSource
from app.tracks import models as track_models
from app.tracks.criteria import criteria_from_dict
from kame_core.sources import get_adapter
from kame_core.sources.http import BlockSignalError

logger = logging.getLogger(__name__)


def _rule_match(job: Job, structured: dict[str, Any]) -> bool:
    """Cheap interim filter until Phase 6 ranking."""
    c = criteria_from_dict(structured)
    title_blob = f"{job.title} {job.normalized_title}".lower()
    if c.titles:
        ok = False
        for t in c.titles:
            if t.exclude:
                if normalize_title(t.title) in job.normalized_title:
                    return False
            elif normalize_title(t.title) in job.normalized_title or t.title.lower() in title_blob:
                ok = True
        if not ok and any(not t.exclude for t in c.titles):
            # soft: also allow skill overlap later; require at least token overlap
            tokens = {w for w in job.normalized_title.split() if len(w) > 2}
            for t in c.titles:
                if t.exclude:
                    continue
                want = {w for w in normalize_title(t.title).split() if len(w) > 2}
                if tokens & want:
                    ok = True
                    break
            if not ok:
                return False
    if c.skills and c.skills.must:
        blob = (job.description_text or "").lower()
        for sk in c.skills.must:
            if sk.lower() not in blob and sk.lower() not in title_blob:
                return False
    if c.work_modes and job.work_mode and job.work_mode not in c.work_modes:
        # remote/hybrid/on_site naming
        wm = set(c.work_modes)
        if job.work_mode == "remote" and "remote" not in wm:
            return False
    if c.companies and c.companies.exclude_agencies:
        # placeholder: agency names often contain "staffing", "recruit"
        name = (job.meta or {}).get("company_name") or ""
        if any(x in name.lower() for x in ("staffing", "recruiting agency", "talent partner")):
            return False
    return True


async def _boards_for_run(session: AsyncSession, limit: int = 8) -> list[CompanyBoard]:
    # Prefer hot, then curated greenhouse/ashby/lever
    rows = (
        (
            await session.execute(
                select(CompanyBoard)
                .where(
                    CompanyBoard.status == "active",
                    CompanyBoard.validation_method.in_(("seed_curated", "api", "user")),
                )
                .order_by(CompanyBoard.poll_tier.asc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    if rows:
        return list(rows)
    return list(
        (
            await session.execute(
                select(CompanyBoard).where(CompanyBoard.status == "active").limit(limit)
            )
        ).scalars()
    )


async def run_discover_track(
    ctx: WorkspaceContext,
    track_id: uuid.UUID,
    *,
    run_id: uuid.UUID | None = None,
    fixture_root: Path | None = None,
    board_limit: int = 6,
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
    try:
        # Board sources enabled for track (or defaults)
        track_sources = (
            await ctx.session.execute(
                select(TrackSource, Source)
                .join(Source)
                .where(TrackSource.track_id == track_id, TrackSource.enabled.is_(True))
            )
        ).all()
        adapter_keys = {s.key for _, s in track_sources if s.enabled_global and not s.circuit_open}
        if not adapter_keys:
            adapter_keys = {
                s.key
                for s in (
                    await ctx.session.execute(
                        select(Source).where(
                            Source.enabled_global.is_(True),
                            Source.circuit_open.is_(False),
                            Source.kind.in_(("ats", "board")),
                        )
                    )
                ).scalars()
            }

        boards = await _boards_for_run(ctx.session, limit=board_limit)
        for board in boards:
            if board.ats not in adapter_keys and "career_jsonld" not in adapter_keys:
                # still allow matching ATS key
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
                    if _rule_match(job, crit.structured):
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
                source.circuit_open = True
                source.block_signals = (source.block_signals or 0) + 1
                source.last_error = str(exc)
                source.last_error_at = datetime.now(UTC)
                source.error_count = (source.error_count or 0) + 1
            except Exception as exc:
                source.last_error = str(exc)[:500]
                source.last_error_at = datetime.now(UTC)
                source.error_count = (source.error_count or 0) + 1
            progress["boards_checked"] = int(progress.get("boards_checked") or 0) + 1
            run.progress = progress
            await ctx.session.flush()

        # Layer-2 boards without slug (remotive etc.) once per run
        for key in ("remotive", "remoteok", "arbeitnow", "jobicy", "muse", "himalayas"):
            if key not in adapter_keys:
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
                async for raw in adapter.discover({}):
                    job, created = await upsert_raw_job(ctx.session, raw)
                    progress["jobs_found"] = int(progress.get("jobs_found") or 0) + 1
                    if created:
                        progress["jobs_new"] = int(progress.get("jobs_new") or 0) + 1
                    if _rule_match(job, crit.structured):
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
            run.progress = progress
            await ctx.session.flush()

        # Phase 6: rank linked jobs for this Track
        try:
            from app.matching.service import score_track_jobs

            score_stats = await score_track_jobs(ctx, track_id, llm_top_n=0)
            progress["scored"] = score_stats.get("scored", 0)
            progress["eligible"] = score_stats.get("eligible", 0)
        except Exception as score_exc:
            progress["score_error"] = str(score_exc)[:200]

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
