"""Workspace, membership, and invitation logic. Runs in the request transaction; every mutation
writes its audit row in the same transaction."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit
from app.auth import tokens
from app.auth.models import User
from app.core.config import Settings
from app.core.errors import AppError
from app.core.mail import Mail, Mailer
from app.core.rls import set_request_context
from app.core.security import WorkspaceContext
from app.workspaces import limits
from app.workspaces.models import Invitation, Workspace, WorkspaceMember

RANK = {"viewer": 0, "member": 1, "admin": 2, "owner": 3}
INVITE_TTL = timedelta(days=7)
MAX_OWNED_TEAM_WORKSPACES = 5
PURGE_AFTER_DAYS = 30


def _now() -> datetime:
    return datetime.now(UTC)


# --- creation / listing (user-scoped; no active workspace yet) ---------------------------------


async def create_workspace(
    db: AsyncSession, *, user_id: uuid.UUID, name: str, kind: str, request_id: str | None
) -> Workspace:
    if kind == "team":
        await set_request_context(db, user_id=str(user_id))
        owned = (
            await db.execute(
                select(func.count())
                .select_from(WorkspaceMember)
                .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
                .where(
                    WorkspaceMember.user_id == user_id,
                    WorkspaceMember.role == "owner",
                    Workspace.kind == "team",
                    Workspace.deleted_at.is_(None),
                )
            )
        ).scalar_one()
        if owned >= MAX_OWNED_TEAM_WORKSPACES:
            raise AppError("workspace_limit", "Workspace limit reached", 409)
    ws_id = uuid.uuid4()
    await set_request_context(db, user_id=str(user_id), workspace_id=str(ws_id))
    ws = Workspace(id=ws_id, name=name, kind=kind, created_by=user_id)
    db.add(ws)
    await db.flush()
    db.add(WorkspaceMember(workspace_id=ws_id, user_id=user_id, role="owner"))
    await db.flush()
    await audit.record_in_workspace(
        db,
        workspace_id=ws_id,
        actor_id=str(user_id),
        request_id=request_id,
        action="workspace.created",
        target_type="workspace",
        target_id=str(ws_id),
        after={"name": name, "kind": kind},
    )
    return ws


async def list_workspaces(db: AsyncSession, user_id: uuid.UUID) -> list[tuple[Workspace, str]]:
    await set_request_context(db, user_id=str(user_id))
    rows = (
        await db.execute(
            select(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.is_active,
                Workspace.deleted_at.is_(None),
            )
            .order_by(Workspace.created_at)
        )
    ).all()
    return [(w, r) for w, r in rows]


# --- active workspace ---------------------------------------------------------------------------


async def get_workspace(ctx: WorkspaceContext) -> Workspace:
    ws = await ctx.session.get(Workspace, ctx.workspace_id)
    if ws is None:
        raise AppError("workspace_not_found", "Workspace not found", 404)
    return ws


async def rename(ctx: WorkspaceContext, name: str) -> Workspace:
    ws = await get_workspace(ctx)
    before = ws.name
    ws.name = name
    await audit.record(
        ctx,
        action="workspace.renamed",
        target_type="workspace",
        target_id=str(ws.id),
        before={"name": before},
        after={"name": name},
    )
    return ws


async def audit_export(ctx: WorkspaceContext) -> None:
    await audit.record(
        ctx, action="workspace.exported", target_type="workspace", target_id=str(ctx.workspace_id)
    )


async def soft_delete(ctx: WorkspaceContext, *, storage=None) -> dict:
    """Hide the workspace and purge R2 objects under ws/<id>/. Rows are hard-removed after 30 days."""
    ws = await get_workspace(ctx)
    if ws.kind == "personal":
        raise AppError("personal_workspace", "A personal workspace cannot be deleted", 409)
    ws.deleted_at = _now()
    purged = 0
    if storage is not None:
        purged = await storage.delete_prefix(f"ws/{ws.id}/")
    await audit.record(
        ctx,
        action="workspace.deleted",
        target_type="workspace",
        target_id=str(ws.id),
        after={"r2_objects_purged": purged},
    )
    return {"r2_objects_purged": purged}


async def purge_deleted_workspaces(session_factory, *, now: datetime | None = None) -> int:
    """Hard-remove workspaces soft-deleted more than 30 days ago. Blobs were removed at delete."""
    cutoff = (now or _now()) - timedelta(days=PURGE_AFTER_DAYS)
    purged = 0
    async with session_factory() as session:
        ids = [
            row[0]
            for row in (
                await session.execute(
                    text("SELECT deleted_workspace_ids_before(:cutoff)"), {"cutoff": cutoff}
                )
            )
        ]
    for wid in ids:
        try:
            async with session_factory() as session, session.begin():
                await set_request_context(session, user_id=None, workspace_id=str(wid))
                result = await session.execute(delete(Workspace).where(Workspace.id == wid))
                purged += int(getattr(result, "rowcount", 0) or 0)
        except Exception:  # noqa: S112 — one bad workspace must not stop the purge
            continue
    return purged


# --- members ------------------------------------------------------------------------------------


async def list_members(ctx: WorkspaceContext) -> list[tuple[WorkspaceMember, User]]:
    rows = (
        await ctx.session.execute(
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == ctx.workspace_id, WorkspaceMember.is_active)
            .order_by(WorkspaceMember.created_at)
        )
    ).all()
    return [(m, u) for m, u in rows]


async def _target(ctx: WorkspaceContext, user_id: uuid.UUID) -> WorkspaceMember:
    m = (
        await ctx.session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == ctx.workspace_id,
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.is_active,
            )
        )
    ).scalar_one_or_none()
    if m is None:
        raise AppError("member_not_found", "Member not found", 404)
    return m


async def change_role(ctx: WorkspaceContext, user_id: uuid.UUID, new_role: str) -> WorkspaceMember:
    if user_id == ctx.user_id:
        raise AppError("forbidden", "You cannot change your own role", 403)
    m = await _target(ctx, user_id)
    # Actors manage only roles strictly below their own, and never grant their own level.
    if RANK[m.role] >= RANK[ctx.role] or RANK[new_role] >= RANK[ctx.role]:
        raise AppError("forbidden", "You do not have permission to do this", 403)
    before = m.role
    m.role = new_role
    await audit.record(
        ctx,
        action="member.role_changed",
        target_type="user",
        target_id=str(user_id),
        before={"role": before},
        after={"role": new_role},
    )
    return m


async def remove_member(ctx: WorkspaceContext, user_id: uuid.UUID) -> None:
    if user_id == ctx.user_id:
        raise AppError("forbidden", "Use leave to remove yourself", 403)
    m = await _target(ctx, user_id)
    if RANK[m.role] >= RANK[ctx.role]:
        raise AppError("forbidden", "You do not have permission to do this", 403)
    await ctx.session.execute(
        delete(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ctx.workspace_id, WorkspaceMember.user_id == user_id
        )
    )
    await audit.record(
        ctx,
        action="member.removed",
        target_type="user",
        target_id=str(user_id),
        before={"role": m.role},
    )


async def leave(ctx: WorkspaceContext) -> None:
    ws = await get_workspace(ctx)
    if ws.kind == "personal":
        raise AppError("personal_workspace", "You cannot leave your personal workspace", 409)
    if ctx.role == "owner":
        raise AppError(
            "owner_must_transfer", "Transfer ownership before leaving this workspace", 409
        )
    await ctx.session.execute(
        delete(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ctx.workspace_id,
            WorkspaceMember.user_id == ctx.user_id,
        )
    )
    await audit.record(
        ctx,
        action="member.left",
        target_type="user",
        target_id=str(ctx.user_id),
        before={"role": ctx.role},
    )


async def transfer_ownership(ctx: WorkspaceContext, user_id: uuid.UUID) -> None:
    ws = await get_workspace(ctx)
    if ws.kind == "personal":
        raise AppError("personal_workspace", "A personal workspace cannot be transferred", 409)
    if user_id == ctx.user_id:
        raise AppError("bad_request", "Pick another member", 400)
    target = await _target(ctx, user_id)
    target.role = "owner"
    await ctx.session.execute(
        update(WorkspaceMember)
        .where(
            WorkspaceMember.workspace_id == ctx.workspace_id,
            WorkspaceMember.user_id == ctx.user_id,
        )
        .values(role="admin")
    )
    await audit.record(
        ctx,
        action="workspace.ownership_transferred",
        target_type="user",
        target_id=str(user_id),
    )


# --- invitations --------------------------------------------------------------------------------


async def invite(
    ctx: WorkspaceContext, settings: Settings, mailer: Mailer, *, email: str, role: str
) -> Invitation:
    if RANK[role] >= RANK[ctx.role]:
        raise AppError("forbidden", "You do not have permission to do this", 403)
    # Mail goes out from our domain: only confirmed accounts may send it.
    inviter = await ctx.session.get(User, ctx.user_id)
    if inviter is None or inviter.email_verified_at is None:
        raise AppError("email_unverified", "Confirm your email first", 409)
    email = email.strip().lower()
    already = (
        await ctx.session.execute(
            select(WorkspaceMember.user_id)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(
                WorkspaceMember.workspace_id == ctx.workspace_id,
                User.email == email,
                WorkspaceMember.is_active,
            )
        )
    ).first()
    if already:
        raise AppError("already_member", "This person is already a member", 409)
    await limits.require_below(
        ctx.session,
        ctx.workspace_id,
        "max_members",
        await limits.member_count(ctx.session, ctx.workspace_id)
        + await limits.pending_invitation_count(ctx.session, ctx.workspace_id),
        "member_limit",
    )
    # One live invitation per email.
    await ctx.session.execute(
        update(Invitation)
        .where(
            Invitation.email == email,
            Invitation.accepted_at.is_(None),
            Invitation.revoked_at.is_(None),
        )
        .values(revoked_at=_now())
    )
    raw, hashed = tokens.new_opaque_token()
    inv = Invitation(
        workspace_id=ctx.workspace_id,
        email=email,
        role=role,
        token_hash=hashed,
        invited_by=ctx.user_id,
        expires_at=_now() + INVITE_TTL,
    )
    ctx.session.add(inv)
    await ctx.session.flush()
    ws = await get_workspace(ctx)
    await audit.record(
        ctx,
        action="invitation.created",
        target_type="invitation",
        target_id=str(inv.id),
        after={"role": role},
    )
    base = settings.web_base_url.rstrip("/")
    await mailer.send(
        Mail(
            email,
            f"You are invited to {ws.name}",
            f"You have been invited to join {ws.name} as {role}.\n\n"
            f"{base}/invite?token={raw}\n\nThe link works once and expires in 7 days.",
        )
    )
    return inv


def _pending():
    return (
        Invitation.accepted_at.is_(None),
        Invitation.revoked_at.is_(None),
        Invitation.expires_at > func.now(),
    )


async def list_invitations(ctx: WorkspaceContext) -> list[Invitation]:
    return list(
        (
            await ctx.session.execute(
                select(Invitation).where(*_pending()).order_by(Invitation.created_at.desc())
            )
        ).scalars()
    )


async def revoke_invitation(ctx: WorkspaceContext, invitation_id: uuid.UUID) -> None:
    inv = (
        await ctx.session.execute(
            select(Invitation).where(Invitation.id == invitation_id, *_pending())
        )
    ).scalar_one_or_none()
    if inv is None:
        raise AppError("invitation_not_found", "Invitation not found", 404)
    inv.revoked_at = _now()
    await audit.record(
        ctx, action="invitation.revoked", target_type="invitation", target_id=str(inv.id)
    )


async def accept_invitation(
    db: AsyncSession, *, user_id: uuid.UUID, raw_token: str, request_id: str | None
) -> tuple[Workspace, str]:
    hashed = tokens.hash_token(raw_token)
    await set_request_context(db, user_id=str(user_id))
    # Lets RLS expose exactly this one invitation before a workspace is active.
    await db.execute(text("SELECT set_config('app.invite_token_hash', :h, true)"), {"h": hashed})
    invalid = AppError("invalid_invitation", "This invitation is invalid or has expired", 400)
    inv = (
        await db.execute(
            select(Invitation).where(Invitation.token_hash == hashed, *_pending()).with_for_update()
        )
    ).scalar_one_or_none()
    if inv is None:
        raise invalid
    user = await db.get(User, user_id)
    # The email binding only means something if the address was proven: otherwise anyone holding
    # a leaked link could register the invited address and walk in.
    if user is None or user.email_verified_at is None:
        raise AppError("email_unverified", "Confirm your email first", 409)
    if user.email.lower() != inv.email.lower():
        raise AppError(
            "invite_email_mismatch", "This invitation was sent to a different email", 403
        )
    await set_request_context(db, user_id=str(user_id), workspace_id=str(inv.workspace_id))
    ws = await db.get(Workspace, inv.workspace_id)
    if ws is None or ws.deleted_at is not None:
        raise invalid
    member = (
        await db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == ws.id, WorkspaceMember.user_id == user_id
            )
        )
    ).scalar_one_or_none()
    if member is None:
        await limits.require_below(
            db, ws.id, "max_members", await limits.member_count(db, ws.id), "member_limit"
        )
        db.add(WorkspaceMember(workspace_id=ws.id, user_id=user_id, role=inv.role))
        role = inv.role
        await audit.record_in_workspace(
            db,
            workspace_id=ws.id,
            actor_id=str(user_id),
            request_id=request_id,
            action="member.joined",
            target_type="invitation",
            target_id=str(inv.id),
            after={"role": role},
        )
    else:
        role = member.role
    inv.accepted_at = _now()
    await db.flush()
    return ws, role
