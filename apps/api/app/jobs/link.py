"""Cheap post-ingest linking: does a job plausibly belong to this Track?"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.models import Job, TrackJob
from app.jobs.normalize import normalize_title
from app.tracks.criteria import criteria_from_dict


def rule_match(job: Job, structured: dict[str, Any]) -> bool:
    """Interim filter before the full ranking pass. Intentionally permissive."""
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
        if job.work_mode == "remote" and "remote" not in set(c.work_modes):
            return False
    if c.companies and c.companies.exclude_agencies:
        name = (job.meta or {}).get("company_name") or ""
        if any(x in name.lower() for x in ("staffing", "recruiting agency", "talent partner")):
            return False
    return True


async def link_track_job(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    track_id: uuid.UUID,
    job: Job,
    structured: dict[str, Any],
) -> bool:
    """Create a TrackJob row when the job fits and none exists. Returns True when linked."""
    if not rule_match(job, structured):
        return False
    existing = (
        await session.execute(
            select(TrackJob).where(TrackJob.track_id == track_id, TrackJob.job_id == job.id)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return False
    session.add(
        TrackJob(
            workspace_id=workspace_id,
            track_id=track_id,
            job_id=job.id,
            status="new",
            score=0.5,
            fit={"method": "rule_v1"},
        )
    )
    return True
