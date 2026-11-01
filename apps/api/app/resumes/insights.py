"""Market insights aggregation from matched Track jobs."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.models import Job, TrackJob
from app.matching.models import JobQualification


async def compute_market_insights(
    session: AsyncSession,
    *,
    track_id,
    profile_skills: set[str],
    resume_skill_names: set[str],
    window_days: int = 30,
) -> dict[str, Any]:
    since = datetime.now(UTC) - timedelta(days=window_days)
    rows = (
        await session.execute(
            select(TrackJob, Job)
            .join(Job, Job.id == TrackJob.job_id)
            .where(
                TrackJob.track_id == track_id,
                TrackJob.eligibility == "eligible",
                Job.status == "open",
                Job.last_seen_at >= since,
            )
        )
    ).all()

    skill_counts: Counter[str] = Counter()
    title_counts: Counter[str] = Counter()
    salaries: list[float] = []
    years: list[float] = []
    certs: Counter[str] = Counter()

    for _tj, job in rows:
        title_counts[job.normalized_title or job.title.lower()] += 1
        for sk in job.skills or []:
            skill_counts[str(sk)] += 1
        sal = job.salary or {}
        if sal.get("min"):
            try:
                salaries.append(float(sal["min"]))
            except (TypeError, ValueError):
                pass
        quals = (
            await session.execute(select(JobQualification).where(JobQualification.job_id == job.id))
        ).scalars()
        for q in quals:
            norm = q.normalized or {}
            if norm.get("type") == "skill" and norm.get("name"):
                skill_counts[str(norm["name"])] += 1
            if norm.get("type") == "years" and norm.get("min") is not None:
                try:
                    years.append(float(norm["min"]))
                except (TypeError, ValueError):
                    pass
            if norm.get("type") == "certification" and norm.get("name"):
                certs[str(norm["name"])] += 1

    sample = len(rows)
    skills_out = []
    for name, freq in skill_counts.most_common(25):
        low = name.lower()
        if low in resume_skill_names or any(low in r for r in resume_skill_names):
            status = "have_shown"
        elif low in profile_skills:
            status = "have_not_shown"
        elif any(low in p or p in low for p in profile_skills):
            status = "adjacent"
        else:
            status = "gap"
        skills_out.append(
            {
                "name": name,
                "frequency": freq,
                "share": round(freq / sample, 3) if sample else 0,
                "status": status,
            }
        )

    titles = [{"title": t, "count": c} for t, c in title_counts.most_common(15)]
    salary: dict[str, Any] = {}
    if salaries:
        salaries.sort()
        salary = {
            "min": salaries[0],
            "max": salaries[-1],
            "median": salaries[len(salaries) // 2],
            "n": len(salaries),
        }
    years_dist: dict[str, Any] = {}
    if years:
        years.sort()
        years_dist = {
            "min": years[0],
            "max": years[-1],
            "median": years[len(years) // 2],
            "n": len(years),
        }

    comparison = {
        "have_shown": [s["name"] for s in skills_out if s["status"] == "have_shown"],
        "have_not_shown": [s["name"] for s in skills_out if s["status"] == "have_not_shown"],
        "adjacent": [s["name"] for s in skills_out if s["status"] == "adjacent"],
        "gap": [s["name"] for s in skills_out if s["status"] == "gap"],
    }

    return {
        "window_days": window_days,
        "sample_size": sample,
        "low_confidence": sample < 30,
        "skills": skills_out,
        "titles": titles,
        "salary": salary,
        "years_required": years_dist,
        "certifications": [{"name": n, "count": c} for n, c in certs.most_common(10)],
        "comparison": comparison,
        "secondary_research": {},
        "computed_at": datetime.now(UTC).isoformat(),
    }
