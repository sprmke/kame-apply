"""Admin ops dashboards: source health, recent workflows, AI cost summary."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.ai.service import usage_summary
from app.core.security import WorkspaceContext, require_action
from app.jobs.models import DiscoveryRun
from app.sources import service as sources_service
from app.sources.schemas import SourceHealthRead

router = APIRouter(prefix="/ops", tags=["ops"])

AdminRead = Depends(require_action("activity.read"))


@router.get("/dashboard")
async def ops_dashboard(ctx: WorkspaceContext = AdminRead):
    sources = await sources_service.list_source_health(ctx.session)
    since = datetime.now(UTC) - timedelta(days=7)
    runs = list(
        (
            await ctx.session.execute(
                select(DiscoveryRun)
                .where(DiscoveryRun.created_at >= since)
                .order_by(DiscoveryRun.created_at.desc())
                .limit(50)
            )
        ).scalars()
    )
    usage = await usage_summary(ctx)
    return {
        "sources": [
            SourceHealthRead.model_validate(s, from_attributes=True).model_dump(mode="json")
            for s in sources
        ],
        "recent_runs": [
            {
                "id": str(r.id),
                "track_id": str(r.track_id),
                "status": r.status,
                "trigger": r.trigger,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "error": r.error,
            }
            for r in runs
        ],
        "ai_cost": {
            "month_start": usage["month_start"].isoformat(),
            "budget_cents": usage["budget_cents"],
            "spent_micros": usage["spent_micros"],
            "by_feature": usage["by_feature"],
            "by_day": [
                {
                    "day": d["day"].isoformat()
                    if hasattr(d["day"], "isoformat")
                    else str(d["day"]),
                    "cost_micros": d["cost_micros"],
                    "calls": d["calls"],
                }
                for d in usage["by_day"]
            ],
        },
    }
