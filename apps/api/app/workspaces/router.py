import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    Principal,
    WorkspaceContext,
    current_principal,
    get_db,
    require_action,
)
from app.workspaces import limits, service
from app.workspaces.export import build_export, export_json_bytes
from app.workspaces.schemas import (
    InvitationCreate,
    InvitationRead,
    InviteAcceptIn,
    LimitsRead,
    MemberRead,
    MemberUpdate,
    OkRead,
    TransferIn,
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceUpdate,
)

# User-scoped: list and create workspaces, accept an invitation (no active workspace yet).
workspaces_router = APIRouter(prefix="/workspaces", tags=["workspaces"])
invitations_router = APIRouter(prefix="/invitations", tags=["invitations"])
# Workspace-scoped: the active workspace comes from the X-Workspace-Id header.
workspace_router = APIRouter(prefix="/workspace", tags=["workspace"])


def _rid(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


@workspaces_router.get("", response_model=list[WorkspaceRead])
async def list_workspaces(
    principal: Principal = Depends(current_principal), db: AsyncSession = Depends(get_db)
):
    rows = await service.list_workspaces(db, principal.user_id)
    return [WorkspaceRead(id=w.id, name=w.name, kind=w.kind, role=r) for w, r in rows]


@workspaces_router.post("", response_model=WorkspaceRead, status_code=201)
async def create_workspace(
    body: WorkspaceCreate,
    request: Request,
    principal: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_db),
):
    ws = await service.create_workspace(
        db, user_id=principal.user_id, name=body.name, kind="team", request_id=_rid(request)
    )
    return WorkspaceRead(id=ws.id, name=ws.name, kind=ws.kind, role="owner")


@invitations_router.post("/accept", response_model=WorkspaceRead)
async def accept_invitation(
    body: InviteAcceptIn,
    request: Request,
    principal: Principal = Depends(current_principal),
    db: AsyncSession = Depends(get_db),
):
    limiter = request.app.state.rate_limiter
    if request.app.state.settings.auth_rate_limit_enabled:
        limiter.check(f"invite-accept:user:{principal.user_id}", limit=10, window_seconds=3600)
    ws, role = await service.accept_invitation(
        db, user_id=principal.user_id, raw_token=body.token, request_id=_rid(request)
    )
    return WorkspaceRead(id=ws.id, name=ws.name, kind=ws.kind, role=role)


@workspace_router.get("", response_model=WorkspaceRead)
async def get_workspace(ctx: WorkspaceContext = Depends(require_action("workspace.read"))):
    ws = await service.get_workspace(ctx)
    return WorkspaceRead(id=ws.id, name=ws.name, kind=ws.kind, role=ctx.role)


@workspace_router.get("/limits", response_model=LimitsRead)
async def get_limits(ctx: WorkspaceContext = Depends(require_action("workspace.read"))):
    caps = await limits.get_limits(ctx.session, ctx.workspace_id)
    return LimitsRead(
        **caps,
        members_used=await limits.member_count(ctx.session, ctx.workspace_id)
        + await limits.pending_invitation_count(ctx.session, ctx.workspace_id),
    )


@workspace_router.patch("", response_model=WorkspaceRead)
async def rename_workspace(
    body: WorkspaceUpdate, ctx: WorkspaceContext = Depends(require_action("workspace.update"))
):
    ws = await service.rename(ctx, body.name)
    return WorkspaceRead(id=ws.id, name=ws.name, kind=ws.kind, role=ctx.role)


@workspace_router.get("/export")
async def export_workspace(ctx: WorkspaceContext = Depends(require_action("workspace.delete"))):
    """Owner-only JSON export of workspace data (no secrets / no R2 bytes)."""
    payload = await build_export(ctx)
    body = export_json_bytes(payload)
    await service.audit_export(ctx)
    return Response(
        content=body,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="kame-apply-{ctx.workspace_id}.json"'
        },
    )


@workspace_router.delete("", response_model=OkRead)
async def delete_workspace(
    request: Request, ctx: WorkspaceContext = Depends(require_action("workspace.delete"))
):
    await service.soft_delete(ctx, storage=request.app.state.storage)
    return OkRead()


@workspace_router.post("/leave", response_model=OkRead)
async def leave_workspace(ctx: WorkspaceContext = Depends(require_action("workspace.leave"))):
    await service.leave(ctx)
    return OkRead()


@workspace_router.post("/transfer", response_model=OkRead)
async def transfer_ownership(
    body: TransferIn, ctx: WorkspaceContext = Depends(require_action("workspace.transfer"))
):
    await service.transfer_ownership(ctx, body.user_id)
    return OkRead()


@workspace_router.get("/members", response_model=list[MemberRead])
async def list_members(ctx: WorkspaceContext = Depends(require_action("members.read"))):
    return [
        MemberRead(user_id=u.id, email=u.email, name=u.name, role=m.role, joined_at=m.created_at)
        for m, u in await service.list_members(ctx)
    ]


@workspace_router.patch("/members/{user_id}", response_model=OkRead)
async def change_member_role(
    user_id: uuid.UUID,
    body: MemberUpdate,
    ctx: WorkspaceContext = Depends(require_action("members.change_role")),
):
    await service.change_role(ctx, user_id, body.role)
    return OkRead()


@workspace_router.delete("/members/{user_id}", response_model=OkRead)
async def remove_member(
    user_id: uuid.UUID, ctx: WorkspaceContext = Depends(require_action("members.remove"))
):
    await service.remove_member(ctx, user_id)
    return OkRead()


@workspace_router.get("/invitations", response_model=list[InvitationRead])
async def list_invitations(ctx: WorkspaceContext = Depends(require_action("members.invite"))):
    return [
        InvitationRead(
            id=i.id, email=i.email, role=i.role, expires_at=i.expires_at, created_at=i.created_at
        )
        for i in await service.list_invitations(ctx)
    ]


@workspace_router.post("/invitations", response_model=InvitationRead, status_code=201)
async def create_invitation(
    body: InvitationCreate,
    request: Request,
    ctx: WorkspaceContext = Depends(require_action("members.invite")),
):
    s = request.app.state
    if s.settings.auth_rate_limit_enabled:
        s.rate_limiter.check(f"invite:user:{ctx.user_id}", limit=20, window_seconds=3600)
        s.rate_limiter.check(f"invite:ws:{ctx.workspace_id}", limit=30, window_seconds=3600)
    inv = await service.invite(ctx, s.settings, s.mailer, email=body.email, role=body.role)
    return InvitationRead(
        id=inv.id,
        email=inv.email,
        role=inv.role,
        expires_at=inv.expires_at,
        created_at=inv.created_at,
    )


@workspace_router.delete("/invitations/{invitation_id}", response_model=OkRead)
async def revoke_invitation(
    invitation_id: uuid.UUID, ctx: WorkspaceContext = Depends(require_action("members.invite"))
):
    await service.revoke_invitation(ctx, invitation_id)
    return OkRead()
