from typing import Any

from sqlalchemy import insert

from app.audit.models import ActivityLog
from app.core.security import WorkspaceContext


async def record(
    ctx: WorkspaceContext,
    *,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    actor_type: str = "user",
) -> None:
    """Append an audit row in the caller's transaction (audit-logging skill).

    Call it from the service function that performs the write, so the event commits or rolls back
    with the change. Never pass secrets, tokens, resume text, or sensitive-class values.
    """
    await record_in_workspace(
        ctx.session,
        workspace_id=ctx.workspace_id,
        actor_id=str(ctx.user_id),
        request_id=ctx.request_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        before=before,
        after=after,
        actor_type=actor_type,
    )


async def record_in_workspace(
    session,
    *,
    workspace_id,
    actor_id: str | None,
    request_id: str | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    actor_type: str = "user",
) -> None:
    """Like `record` for flows that have no WorkspaceContext yet (workspace creation, accepting an
    invitation). The transaction's app.workspace_id must already equal `workspace_id`."""
    await session.execute(
        insert(ActivityLog).values(
            workspace_id=workspace_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            before=before,
            after=after,
            request_id=request_id,
        )
    )


async def record_platform(
    session,
    *,
    action: str,
    actor_id: str | None,
    request_id: str | None,
    target_type: str | None = None,
    target_id: str | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    """Append a platform-level event (no workspace), e.g. sign-in, for events that precede or span
    workspaces. RLS lets tenants insert but never read these rows. Same rules: no secrets or PII
    beyond ids."""
    await session.execute(
        insert(ActivityLog).values(
            workspace_id=None,
            actor_type="user" if actor_id else "system",
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            after=after,
            request_id=request_id,
        )
    )
