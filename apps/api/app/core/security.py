"""Request-scoped identity, workspace context, and RBAC dependencies.

Order matters and is the whole point of this module:
  1. authenticate -> user id
  2. set app.user_id           (RLS lets the user see only their own memberships)
  3. look up an active membership for the requested workspace (404 if none: no existence leak)
  4. set app.workspace_id      (only now do tenant tables become visible)
  5. check the role against the RBAC table
"""

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

from fastapi import Depends, Header, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.tokens import decode_access_token
from app.core.errors import AppError
from app.core.rbac import can
from app.core.rls import set_request_context


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    """One transaction per request: commit on success, roll back on any exception."""
    async with request.app.state.session_factory() as session, session.begin():
        yield session


@dataclass(frozen=True)
class Principal:
    user_id: uuid.UUID
    session_id: uuid.UUID


async def current_principal(
    request: Request,
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_db),
) -> Principal:
    """Verify the bearer access token AND that its session is still live and the user active, so
    revoking a session or deactivating a user takes effect immediately."""
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AppError("unauthenticated", "Authentication required", 401)
    user_id, session_id = decode_access_token(request.app.state.settings, token)
    live = (
        await session.execute(
            text(
                "SELECT 1 FROM user_sessions s JOIN users u ON u.id = s.user_id "
                "WHERE s.id = :sid AND s.user_id = :uid AND s.revoked_at IS NULL AND u.is_active"
            ),
            {"sid": session_id, "uid": user_id},
        )
    ).first()
    if live is None:
        raise AppError("unauthenticated", "Authentication required", 401)
    return Principal(user_id, session_id)


async def current_user_id(principal: Principal = Depends(current_principal)) -> uuid.UUID:
    """Authenticated user id. Tests override this to skip token minting."""
    return principal.user_id


@dataclass(frozen=True)
class WorkspaceContext:
    session: AsyncSession
    user_id: uuid.UUID
    workspace_id: uuid.UUID
    role: str
    request_id: str | None
    # "user" (JWT), "runner" (scoped runner token), or "extension" (scoped extension token).
    auth_kind: str = "user"


def _parse_workspace_id(raw: str | None) -> uuid.UUID:
    try:
        return uuid.UUID(raw or "")
    except ValueError:
        raise AppError(
            "workspace_required", "A valid X-Workspace-Id header is required", 400
        ) from None


async def workspace_context(
    request: Request,
    x_workspace_id: str | None = Header(default=None),
    user_id: uuid.UUID = Depends(current_user_id),
    session: AsyncSession = Depends(get_db),
) -> WorkspaceContext:
    workspace_id = _parse_workspace_id(x_workspace_id)
    await set_request_context(session, user_id=str(user_id))
    row = (
        await session.execute(
            text(
                "SELECT m.role FROM workspace_members m "
                "JOIN users u ON u.id = m.user_id AND u.is_active "
                "WHERE m.workspace_id = :wid AND m.user_id = :uid AND m.is_active"
            ),
            {"wid": workspace_id, "uid": user_id},
        )
    ).first()
    if row is None:
        # Same response whether the workspace does not exist or the user is not a member.
        raise AppError("workspace_not_found", "Workspace not found", 404)
    await set_request_context(session, user_id=str(user_id), workspace_id=str(workspace_id))
    deleted = (
        await session.execute(
            text("SELECT deleted_at IS NOT NULL FROM workspaces WHERE id = :wid"),
            {"wid": workspace_id},
        )
    ).scalar_one_or_none()
    if deleted is None or deleted:
        raise AppError("workspace_not_found", "Workspace not found", 404)
    return WorkspaceContext(
        session=session,
        user_id=user_id,
        workspace_id=workspace_id,
        role=row[0],
        request_id=getattr(request.state, "request_id", None),
    )


def require_action(action: str):
    """Dependency factory: the caller's role must be allowed `action` (see app/core/rbac.py)."""

    async def _dep(ctx: WorkspaceContext = Depends(workspace_context)) -> WorkspaceContext:
        if not can(ctx.role, action):
            raise AppError("forbidden", "You do not have permission to do this", 403)
        return ctx

    return _dep
