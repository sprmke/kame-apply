"""Closed-job detection: two consecutive misses on a feed close the job."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.jobs.ingest import mark_missed_jobs
from app.jobs.models import Job, JobSource
from app.sources.models import Source
from tests.conftest import TEST_OWNER_URL


def _job() -> Job:
    key = uuid.uuid4().hex
    return Job(
        title="Backend Engineer",
        normalized_title="backend engineer",
        content_hash=f"closed-{key}",
        canonical_url=f"https://example.com/jobs/{key}",
        apply_url=f"https://example.com/jobs/{key}/apply",
        status="open",
    )


async def test_two_misses_close_a_job_and_a_seen_job_stays_open():
    engine = create_async_engine(TEST_OWNER_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session, session.begin():
        source = Source(
            key=f"feed-{uuid.uuid4().hex[:8]}",
            name="Feed",
            kind="board",
            adapter="board",
        )
        session.add(source)
        job = _job()
        other = _job()
        session.add_all([job, other])
        await session.flush()
        session.add_all(
            [
                JobSource(
                    job_id=job.id,
                    source_id=source.id,
                    external_id="ext-1",
                    url=job.canonical_url,
                ),
                JobSource(
                    job_id=other.id,
                    source_id=source.id,
                    external_id="ext-2",
                    url=other.canonical_url,
                ),
            ]
        )
        await session.flush()

        closed = await mark_missed_jobs(
            session,
            source_id=source.id,
            board_id=None,
            seen_external_ids={"ext-2"},
        )
        assert closed == 0
        assert job.status == "open" and job.miss_streak == 1
        assert other.status == "open" and other.miss_streak == 0

        closed = await mark_missed_jobs(
            session,
            source_id=source.id,
            board_id=None,
            seen_external_ids={"ext-2"},
        )
        assert closed == 1
        assert job.status == "closed" and job.closed_at is not None
        assert other.status == "open"
    await engine.dispose()
