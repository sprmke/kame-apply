"""Freshness labels for postings (apply early boost)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.strategy.schemas import FreshnessRead


def freshness_for(
    *, job_id, posted_at: datetime | None, first_seen_at: datetime | None
) -> FreshnessRead:
    ref = posted_at or first_seen_at
    if ref is None:
        return FreshnessRead(job_id=job_id, label="Unknown age", hours_ago=None, boost="none")
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=UTC)
    hours = (datetime.now(UTC) - ref).total_seconds() / 3600.0
    if hours <= 24:
        return FreshnessRead(
            job_id=job_id,
            label=f"Posted {max(1, int(hours))}h ago" if hours >= 1 else "Posted just now",
            hours_ago=round(hours, 1),
            boost="high",
        )
    if hours <= 72:
        return FreshnessRead(
            job_id=job_id,
            label=f"Posted {int(hours)}h ago",
            hours_ago=round(hours, 1),
            boost="medium",
        )
    days = int(hours / 24)
    if days <= 14:
        return FreshnessRead(
            job_id=job_id, label=f"Posted {days}d ago", hours_ago=round(hours, 1), boost="low"
        )
    return FreshnessRead(
        job_id=job_id, label=f"Posted {days}d ago", hours_ago=round(hours, 1), boost="none"
    )
