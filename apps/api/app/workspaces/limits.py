"""Workspace caps. Defaults live in DEFAULT_LIMITS; a `workspace_limits` row (set by the platform,
read-only for the app role) overrides them. Enforce a cap with `await require_below(...)`."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.workspaces.models import DEFAULT_LIMITS, Invitation, WorkspaceLimits, WorkspaceMember


async def get_limits(session: AsyncSession, workspace_id: uuid.UUID) -> dict[str, int]:
    row = await session.get(WorkspaceLimits, workspace_id)
    if row is None:
        return dict(DEFAULT_LIMITS)
    return {k: getattr(row, k) for k in DEFAULT_LIMITS}


async def require_below(
    session: AsyncSession, workspace_id: uuid.UUID, limit_name: str, current: int, code: str
) -> None:
    cap = (await get_limits(session, workspace_id))[limit_name]
    if current >= cap:
        raise AppError(code, "Workspace limit reached", 409, {"limit": limit_name, "cap": cap})


async def member_count(session: AsyncSession, workspace_id: uuid.UUID) -> int:
    return (
        await session.execute(
            select(func.count())
            .select_from(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.is_active)
        )
    ).scalar_one()


async def pending_invitation_count(session: AsyncSession, workspace_id: uuid.UUID) -> int:
    return (
        await session.execute(
            select(func.count())
            .select_from(Invitation)
            .where(
                Invitation.workspace_id == workspace_id,
                Invitation.accepted_at.is_(None),
                Invitation.revoked_at.is_(None),
                Invitation.expires_at > func.now(),
            )
        )
    ).scalar_one()
