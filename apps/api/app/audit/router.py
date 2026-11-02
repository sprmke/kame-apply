import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, or_, select

from app.audit.models import ActivityLog
from app.core.security import WorkspaceContext, require_action

router = APIRouter(prefix="/activity", tags=["activity"])


class ActivityRead(BaseModel):
    id: uuid.UUID
    actor_type: str
    actor_id: str | None
    action: str
    target_type: str | None
    target_id: str | None
    before: dict | None
    after: dict | None
    request_id: str | None
    created_at: datetime


class ActivityPage(BaseModel):
    items: list[ActivityRead]
    next_before: datetime | None
    # Compound cursor: rows written in one transaction share created_at, so the id breaks the tie
    # and a page boundary cannot silently drop rows.
    next_before_id: uuid.UUID | None = None


@router.get("", response_model=ActivityPage)
async def list_activity(
    action: str | None = Query(
        default=None, max_length=96, description="exact or prefix ending in '.'"
    ),
    target_type: str | None = Query(default=None, max_length=48),
    actor_id: str | None = Query(default=None, max_length=64),
    before: datetime | None = None,
    before_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    ctx: WorkspaceContext = Depends(require_action("activity.read")),
):
    """Newest first, keyset-paginated by `(created_at, id)`. RLS already scopes the rows."""
    q = select(ActivityLog).order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
    if action:
        q = q.where(
            ActivityLog.action.startswith(action)
            if action.endswith(".")
            else ActivityLog.action == action
        )
    if target_type:
        q = q.where(ActivityLog.target_type == target_type)
    if actor_id:
        q = q.where(ActivityLog.actor_id == actor_id)
    if before:
        if before_id:
            q = q.where(
                or_(
                    ActivityLog.created_at < before,
                    and_(ActivityLog.created_at == before, ActivityLog.id < before_id),
                )
            )
        else:
            q = q.where(ActivityLog.created_at < before)
    rows = list((await ctx.session.execute(q.limit(limit + 1))).scalars())
    page, more = rows[:limit], len(rows) > limit
    return ActivityPage(
        items=[ActivityRead.model_validate(r, from_attributes=True) for r in page],
        next_before=page[-1].created_at if more and page else None,
        next_before_id=page[-1].id if more and page else None,
    )
