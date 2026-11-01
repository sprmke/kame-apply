"""Upsert RawJob into global jobs + job_sources with dedupe."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.companies.models import Company
from app.jobs.dedupe import company_norm, prefer_apply_url, same_job
from app.jobs.models import Job, JobSource
from app.jobs.normalize import normalize_raw
from app.sources.models import Source
from kame_core.sources.base import RawJob


async def _get_source(session: AsyncSession, key: str) -> Source | None:
    return (await session.execute(select(Source).where(Source.key == key))).scalar_one_or_none()


async def _resolve_company(session: AsyncSession, name: str, domain: str | None) -> Company:
    nn = company_norm(name) or "unknown"
    q = select(Company).where(Company.normalized_name == nn)
    if domain:
        q = select(Company).where((Company.domain == domain) | (Company.normalized_name == nn))
    row = (await session.execute(q.limit(1))).scalar_one_or_none()
    if row:
        return row
    row = Company(name=name or "Unknown", normalized_name=nn, domain=domain)
    session.add(row)
    await session.flush()
    return row


async def upsert_raw_job(
    session: AsyncSession,
    raw: RawJob,
    *,
    board_id: uuid.UUID | None = None,
) -> tuple[Job, bool]:
    """Returns (job, created_new_job)."""
    norm = normalize_raw(raw)
    source = await _get_source(session, raw.source_key)
    if source is None:
        raise ValueError(f"unknown source {raw.source_key}")

    # Exact external id match
    existing_js = (
        await session.execute(
            select(JobSource).where(
                JobSource.source_id == source.id,
                JobSource.external_id == raw.external_id,
            )
        )
    ).scalar_one_or_none()
    now = datetime.now(UTC)
    if existing_js:
        job = await session.get(Job, existing_js.job_id)
        assert job is not None
        existing_js.last_seen_at = now
        existing_js.url = raw.url or existing_js.url
        job.last_seen_at = now
        job.miss_streak = 0
        if job.status == "closed":
            job.status = "open"
            job.closed_at = None
        await session.flush()
        return job, False

    company = await _resolve_company(session, norm["company_name"], raw.company_domain)

    # Fuzzy: same company + title + simhash
    candidates = (
        (
            await session.execute(
                select(Job)
                .where(
                    Job.company_id == company.id,
                    Job.normalized_title == norm["normalized_title"],
                    Job.status == "open",
                )
                .limit(20)
            )
        )
        .scalars()
        .all()
    )
    match: Job | None = None
    for cand in candidates:
        if same_job(
            company_a=company.normalized_name,
            title_a=cand.title,
            simhash_a=cand.simhash or 0,
            company_b=company.normalized_name,
            title_b=norm["title"],
            simhash_b=norm["simhash"] or 0,
        ):
            match = cand
            break

    created = False
    if match is None:
        created = True
        match = Job(
            company_id=company.id,
            title=norm["title"],
            normalized_title=norm["normalized_title"],
            seniority=norm["seniority"],
            employment_type=norm["employment_type"],
            work_mode=norm["work_mode"],
            locations=norm["locations"],
            remote_eligibility=norm["remote_eligibility"],
            salary=norm["salary"],
            description_html=norm["description_html"],
            description_text=norm["description_text"],
            content_hash=norm["content_hash"],
            simhash=norm["simhash"],
            canonical_url=norm["canonical_url"],
            apply_url=norm["apply_url"],
            posted_at=norm["posted_at"],
            expires_at=norm["expires_at"],
            last_seen_at=now,
            first_seen_at=now,
        )
        session.add(match)
        await session.flush()
    else:
        match.last_seen_at = now
        match.miss_streak = 0

    session.add(
        JobSource(
            job_id=match.id,
            source_id=source.id,
            external_id=raw.external_id,
            url=raw.url or raw.apply_url,
            board_id=board_id,
            first_seen_at=now,
            last_seen_at=now,
            raw={"title": raw.title},
        )
    )
    # Prefer ATS apply URL
    links = (
        await session.execute(
            select(JobSource, Source).join(Source).where(JobSource.job_id == match.id)
        )
    ).all()
    preferred = prefer_apply_url(
        [(s.key, js.url) for js, s in links] + [(raw.source_key, raw.apply_url)]
    )
    if preferred:
        match.apply_url = preferred
        # Canonical prefers ATS host when possible
        if raw.ats:
            match.canonical_url = preferred
    await session.flush()
    source.jobs_ingested = (source.jobs_ingested or 0) + 1
    return match, created


async def mark_missed_jobs(
    session: AsyncSession,
    *,
    source_id: uuid.UUID,
    board_id: uuid.UUID | None,
    seen_external_ids: set[str],
) -> int:
    """Bump miss_streak for jobs on this board/source not seen; close after 2 misses."""
    q = select(JobSource).where(JobSource.source_id == source_id)
    if board_id:
        q = q.where(JobSource.board_id == board_id)
    rows = (await session.execute(q)).scalars().all()
    closed = 0
    now = datetime.now(UTC)
    for js in rows:
        if js.external_id in seen_external_ids:
            continue
        job = await session.get(Job, js.job_id)
        if job is None or job.status != "open":
            continue
        job.miss_streak = (job.miss_streak or 0) + 1
        if job.miss_streak >= 2:
            job.status = "closed"
            job.closed_at = now
            closed += 1
    await session.flush()
    return closed
