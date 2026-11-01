"""Auth for extension API: JWT session or scoped extension token."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, Header, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.rbac import can
from app.core.rls import set_request_context
from app.core.security import (
    WorkspaceContext,
    current_principal,
    get_db,
    workspace_context,
)
from app.extension.models import ExtensionToken
from app.extension.tokens import hash_token, looks_like_extension_token


async def extension_workspace_context(
    request: Request,
    authorization: str | None = Header(default=None),
    x_workspace_id: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
) -> WorkspaceContext:
    """Accept either a normal JWT (+ X-Workspace-Id) or a `ka_ext_` token."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() == "bearer" and looks_like_extension_token(token):
        return await _from_extension_token(
            request, session, raw=token, x_workspace_id=x_workspace_id
        )
    principal = await current_principal(request, authorization, session)
    return await workspace_context(
        request=request,
        x_workspace_id=x_workspace_id,
        user_id=principal.user_id,
        session=session,
    )


async def _from_extension_token(
    request: Request,
    session: AsyncSession,
    *,
    raw: str,
    x_workspace_id: str | None,
) -> WorkspaceContext:
    # Hash lookup may run before tenant context is set (policy allows when both unset).
    await set_request_context(session, user_id=None, workspace_id=None)
    row = (
        await session.execute(
            select(ExtensionToken).where(ExtensionToken.token_hash == hash_token(raw))
        )
    ).scalar_one_or_none()
    if row is None or row.revoked_at is not None:
        raise AppError("unauthenticated", "Authentication required", 401)
    if row.expires_at and row.expires_at < datetime.now(UTC):
        raise AppError("unauthenticated", "Extension token expired", 401)
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
    row.last_used_at = datetime.now(UTC)
    await session.flush()
    return WorkspaceContext(
        session=session,
        user_id=row.user_id,
        workspace_id=row.workspace_id,
        role=membership[0],
        request_id=getattr(request.state, "request_id", None),
    )


def require_extension_action(action: str):
    async def _dep(
        ctx: WorkspaceContext = Depends(extension_workspace_context),
    ) -> WorkspaceContext:
        if not can(ctx.role, action):
            raise AppError("forbidden", "You do not have permission to do this", 403)
        return ctx

    return _dep
