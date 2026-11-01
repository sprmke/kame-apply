"""REST surface for OAuth consent, connected agents, routing, inbox status."""

# ruff: noqa: S106

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, update

from app.agent_bridge import inbox as inbox_svc
from app.agent_bridge import schemas as s
from app.agent_bridge.models import OAuthClient, OAuthPendingAuth, OAuthToken
from app.agent_bridge.oauth_provider import complete_consent
from app.agent_bridge.scopes import ALL_SCOPES, DEFAULT_CONSENT_SCOPES
from app.agent_bridge.tokens import hash_token, new_token
from app.audit import service as audit
from app.core.errors import AppError
from app.core.ratelimit import client_ip
from app.core.security import WorkspaceContext, require_action

router = APIRouter(prefix="/agent-bridge", tags=["agent-bridge"])

Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))
Manage = Depends(require_action("workspace.update"))


@router.get("/pending/{pending_id}", response_model=s.PendingAuthRead)
async def get_pending(pending_id: uuid.UUID, ctx: WorkspaceContext = Write):
    row = await ctx.session.get(OAuthPendingAuth, pending_id)
    if row is None or row.expires_at < datetime.now(UTC):
        raise AppError("not_found", "Authorization request not found or expired", 404)
    client = await ctx.session.get(OAuthClient, row.client_id)
    return s.PendingAuthRead(
        id=row.id,
        client_id=row.client_id,
        client_name=(client.client_name if client else "") or row.client_id,
        scopes=list(row.scopes or []),
        redirect_uri=row.redirect_uri,
        expires_at=row.expires_at,
    )


@router.post("/consent", response_model=s.ConsentResult)
async def consent(request: Request, body: s.ConsentBody, ctx: WorkspaceContext = Write):
    request.app.state.rate_limiter.check(
        f"agent-bridge:consent:{client_ip(request)}:{ctx.user_id}",
        limit=30,
        window_seconds=60,
    )
    if body.workspace_id != ctx.workspace_id:
        raise AppError("forbidden", "Workspace mismatch", 403)
    # Confirm profile belongs to this workspace via RLS-scoped lookup
    from app.profiles.models import CandidateProfile

    profile = await ctx.session.get(CandidateProfile, body.profile_id)
    if profile is None or profile.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Profile not found", 404)
    scopes = [x for x in body.scopes if x in ALL_SCOPES] or list(DEFAULT_CONSENT_SCOPES)
    try:
        redirect = await complete_consent(
            ctx.session,
            pending_id=body.pending_id,
            user_id=ctx.user_id,
            workspace_id=ctx.workspace_id,
            profile_id=body.profile_id,
            scopes=scopes,
        )
    except ValueError:
        raise AppError("not_found", "Authorization request not found or expired", 404) from None
    await audit.record(
        ctx,
        action="agent_bridge.oauth.consent",
        target_type="oauth_pending",
        target_id=str(body.pending_id),
        after={"profile_id": str(body.profile_id), "scopes": scopes},
    )
    return s.ConsentResult(redirect_url=redirect)


@router.get("/tokens", response_model=list[s.TokenRead])
async def list_tokens(ctx: WorkspaceContext = Manage):
    rows = (
        await ctx.session.execute(
            select(OAuthToken, OAuthClient)
            .outerjoin(OAuthClient, OAuthClient.id == OAuthToken.client_id)
            .where(
                OAuthToken.workspace_id == ctx.workspace_id,
                OAuthToken.user_id == ctx.user_id,
                OAuthToken.token_kind.in_(("access", "pat")),
                OAuthToken.revoked_at.is_(None),
            )
            .order_by(OAuthToken.created_at.desc())
        )
    ).all()
    out: list[s.TokenRead] = []
    for tok, client in rows:
        out.append(
            s.TokenRead(
                id=tok.id,
                client_id=tok.client_id,
                client_name=(client.client_name if client else "") or tok.client_id,
                token_kind=tok.token_kind,
                scopes=list(tok.scopes or []),
                created_at=tok.created_at,
                last_used_at=tok.last_used_at,
                expires_at=tok.expires_at,
            )
        )
    return out


@router.post("/tokens/{token_id}/revoke", status_code=204)
async def revoke_token(token_id: uuid.UUID, ctx: WorkspaceContext = Manage):
    row = await ctx.session.get(OAuthToken, token_id)
    if row is None or row.workspace_id != ctx.workspace_id or row.user_id != ctx.user_id:
        raise AppError("not_found", "Token not found", 404)
    now = datetime.now(UTC)
    row.revoked_at = now
    if row.refresh_family_id:
        await ctx.session.execute(
            update(OAuthToken)
            .where(
                OAuthToken.refresh_family_id == row.refresh_family_id,
                OAuthToken.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
    await audit.record(
        ctx,
        action="agent_bridge.token.revoked",
        target_type="oauth_token",
        target_id=str(token_id),
        after={"client_id": row.client_id},
    )


@router.post("/pats", response_model=s.PatCreated)
async def create_pat(request: Request, body: s.PatCreate, ctx: WorkspaceContext = Manage):
    request.app.state.rate_limiter.check(
        f"agent-bridge:pat:{client_ip(request)}:{ctx.user_id}",
        limit=10,
        window_seconds=3600,
    )
    from app.profiles.models import CandidateProfile

    profile = await ctx.session.get(CandidateProfile, body.profile_id)
    if profile is None or profile.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Profile not found", 404)
    # Ensure a synthetic client exists for PATs (oauth_clients has no RLS).
    client_id = "kame-pat"
    if await ctx.session.get(OAuthClient, client_id) is None:
        ctx.session.add(
            OAuthClient(
                id=client_id,
                client_name=body.label or "Personal access token",
                redirect_uris=[],
                grant_types=["client_credentials"],
                response_types=[],
                token_endpoint_auth_method="none",
                scope=" ".join(ALL_SCOPES),
            )
        )
        await ctx.session.flush()
    scopes = [x for x in body.scopes if x in ALL_SCOPES] or list(DEFAULT_CONSENT_SCOPES)
    raw = new_token("kap")
    row = OAuthToken(
        token_hash=hash_token(raw),
        token_kind="pat",
        client_id=client_id,
        user_id=ctx.user_id,
        workspace_id=ctx.workspace_id,
        profile_id=body.profile_id,
        scopes=scopes,
        expires_at=datetime.now(UTC) + timedelta(days=365),
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="agent_bridge.pat.created",
        target_type="oauth_token",
        target_id=str(row.id),
        after={"scopes": scopes},
    )
    return s.PatCreated(id=row.id, token=raw, scopes=scopes)


@router.get("/routing", response_model=list[s.RoutingItem])
async def get_routing(ctx: WorkspaceContext = Read):
    rows = await inbox_svc.get_routing(ctx)
    return [s.RoutingItem(**r) for r in rows]


@router.put("/routing", response_model=s.RoutingItem)
async def put_routing(body: s.RoutingPut, ctx: WorkspaceContext = Manage):
    row = await inbox_svc.put_routing(
        ctx, feature=body.feature, route=body.route, fallback=body.fallback
    )
    return s.RoutingItem(**row)


@router.get("/inbox", response_model=s.InboxStatus)
async def inbox_status(ctx: WorkspaceContext = Read):
    data = await inbox_svc.inbox_status(ctx)
    return s.InboxStatus(**data)


@router.post("/inbox/tasks", status_code=201)
async def enqueue_task(body: s.AgentTaskCreate, ctx: WorkspaceContext = Write):
    task = await inbox_svc.create_task(
        ctx,
        profile_id=body.profile_id,
        kind=body.kind,
        input_data=body.input,
        priority=body.priority,
        fallback_enabled=body.fallback_enabled,
    )
    return inbox_svc.task_to_dict(task)


@router.get("/scopes")
async def list_scopes(ctx: WorkspaceContext = Read):
    return {"scopes": list(ALL_SCOPES), "defaults": list(DEFAULT_CONSENT_SCOPES)}
