"""Per-request WorkspaceContext from an MCP OAuth access token."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from mcp.server.auth.middleware.auth_context import get_access_token
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent_bridge.scopes import TOOL_SCOPES, has_scope
from app.agent_bridge.tokens import parse_subject
from app.core.errors import AppError
from app.core.rls import set_request_context
from app.core.security import WorkspaceContext


@dataclass(frozen=True)
class AgentBridgeContext:
    ctx: WorkspaceContext
    profile_id: uuid.UUID
    scopes: list[str]
    client_id: str
    token_id: str | None


@asynccontextmanager
async def agent_session(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    tool_name: str,
) -> AsyncIterator[AgentBridgeContext]:
    token = get_access_token()
    if token is None:
        raise AppError("unauthenticated", "MCP authentication required", 401)
    required = TOOL_SCOPES.get(tool_name, frozenset({"admin"}))
    if not has_scope(token.scopes or [], required):
        raise AppError("forbidden", f"Missing scope for {tool_name}", 403)
    user_s, ws_s, profile_s = parse_subject(token.subject or "")
    user_id = uuid.UUID(user_s)
    workspace_id = uuid.UUID(ws_s)
    profile_id = uuid.UUID(profile_s)
    async with session_factory() as session, session.begin():
        await set_request_context(session, user_id=str(user_id), workspace_id=str(workspace_id))
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
            raise AppError("workspace_not_found", "Workspace not found", 404)
        claims: dict[str, Any] = token.claims or {}
        yield AgentBridgeContext(
            ctx=WorkspaceContext(
                session=session,
                user_id=user_id,
                workspace_id=workspace_id,
                role=row[0],
                request_id=None,
            ),
            profile_id=profile_id,
            scopes=list(token.scopes or []),
            client_id=token.client_id,
            token_id=str(claims.get("token_id")) if claims.get("token_id") else None,
        )
