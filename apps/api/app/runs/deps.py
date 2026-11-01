"""Auth for runner API: JWT session or scoped runner token."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, Header, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.rbac import can
from app.core.rls import set_request_context
from app.core.security import WorkspaceContext, current_principal, get_db, workspace_context
from app.extension.models import RunnerToken
from app.runs.tokens import hash_token, looks_like_runner_token


async def runner_workspace_context(
    request: Request,
    authorization: str | None = Header(default=None),
    x_workspace_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
) -> WorkspaceContext:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() == "bearer" and looks_like_runner_token(token):
        return await _from_runner_token(request, session, raw=token, x_workspace_id=x_workspace_id)
    principal = await current_principal(request, authorization, session)
    return await workspace_context(
        request=request,
        x_workspace_id=x_workspace_id,
        user_id=principal.user_id,
        session=session,
    )


async def _from_runner_token(
    request: Request,
    session: AsyncSession,
    *,
    raw: str,
    x_workspace_id: str | None,
) -> WorkspaceContext:
    await set_request_context(session, user_id=None, workspace_id=None)
    row = (
        await session.execute(select(RunnerToken).where(RunnerToken.token_hash == hash_token(raw)))
    ).scalar_one_or_none()
    if row is None or row.revoked_at is not None:
        raise AppError("unauthenticated", "Authentication required", 401)
    if x_workspace_id and str(row.workspace_id) != x_workspace_id:
        raise AppError("forbidden", "Workspace mismatch", 403)

    await set_request_context(session, user_id=str(row.user_id))
    membership = (
        await session.execute(
            text(
                "SELECT m.role FROM workspace_members m "
                "JOIN users u ON u.id = m.user_id AND u.is_active "
                "WHERE m.workspace_id = :wid AND m.user_id = :uid AND m.is_active"
            ),
            {"wid": row.workspace_id, "uid": row.user_id},
        )
    ).first()
    if membership is None:
        raise AppError("workspace_not_found", "Workspace not found", 404)
    await set_request_context(session, user_id=str(row.user_id), workspace_id=str(row.workspace_id))
    row.last_seen_at = datetime.now(UTC)
    await session.flush()
    return WorkspaceContext(
        session=session,
        user_id=row.user_id,
        workspace_id=row.workspace_id,
        role=membership[0],
        request_id=getattr(request.state, "request_id", None),
    )


def require_runner_action(action: str):
    async def _dep(ctx: WorkspaceContext = Depends(runner_workspace_context)) -> WorkspaceContext:
        if not can(ctx.role, action):
            raise AppError("forbidden", "You do not have permission to do this", 403)
        return ctx

    return _dep
