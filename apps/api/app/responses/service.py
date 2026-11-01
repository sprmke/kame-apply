"""Ingest recruiter replies, classify, propose status changes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.applications import status as sm
from app.applications import tracker
from app.applications.models import Application
from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.responses import models as m
from app.responses.classify import CLASS_TO_STATUS, classify_reply
from app.responses.schemas import (
    ResponseMessageRead,
    StatusProposalRead,
)

# When the classifier wants a status that is not a direct transition, pick a bridge.
_BRIDGES: dict[tuple[str, str], str] = {
    ("submitted", "offer"): "interview",
    ("responded", "rejected"): "rejected",
    ("ghosted", "offer"): "interview",
}


def _msg_read(row: m.ResponseMessage) -> ResponseMessageRead:
    return ResponseMessageRead.model_validate(row)


def _prop_read(row: m.StatusProposal, app: Application | None = None) -> StatusProposalRead:
    data = StatusProposalRead.model_validate(row)
    if app is not None:
        data.company_name = app.company_name or ""
        data.job_title = app.job_title or ""
    return data


def _proposed_status(current: str, desired: str | None) -> str | None:
    if not desired:
        return None
    cur = sm.normalize(current)
    want = sm.normalize(desired)
    if want == cur:
        return None
    allowed = sm.ALLOWED.get(cur, set())
    if want in allowed:
        return want
    bridge = _BRIDGES.get((cur, want))
    if bridge and bridge in allowed:
        return bridge
    if (cur, want) in sm.REGRESSIONS:
        return want
    return None


async def ingest_reply(
    ctx: WorkspaceContext,
    *,
    application_id: uuid.UUID | None,
    sender: str,
    subject: str,
    body_text: str,
) -> tuple[ResponseMessageRead, StatusProposalRead | None]:
    app: Application | None = None
    if application_id is not None:
        app = await ctx.session.get(Application, application_id)
        if app is None or app.workspace_id != ctx.workspace_id:
            raise AppError("not_found", "Application not found", 404)

    result = classify_reply(subject=subject, body=body_text)
    msg = m.ResponseMessage(
        workspace_id=ctx.workspace_id,
        application_id=application_id,
        sender=(sender or "")[:500],
        subject=(subject or "")[:500],
        body_text=(body_text or "")[:50_000],
        classification=result.classification,
        confidence=result.confidence,
        scam_level=result.scam_level,
        scam_reasons=result.scam_reasons,
    )
    ctx.session.add(msg)
    await ctx.session.flush()

    proposal: m.StatusProposal | None = None
    desired = CLASS_TO_STATUS.get(result.classification)
    if app is not None and desired and result.scam_level != "red":
        target = _proposed_status(app.status, desired)
        if target:
            proposal = m.StatusProposal(
                workspace_id=ctx.workspace_id,
                application_id=app.id,
                response_message_id=msg.id,
                from_status=sm.normalize(app.status),
                to_status=target,
                reason=f"Classified as {result.classification}",
                citation=result.citation,
                status="pending",
            )
            ctx.session.add(proposal)
            await ctx.session.flush()

    await audit.record(
        ctx,
        action="response.ingested",
        target_type="response_message",
        target_id=str(msg.id),
        after={
            "classification": result.classification,
            "confidence": result.confidence,
            "scam_level": result.scam_level,
            "application_id": str(application_id) if application_id else None,
            "proposal_id": str(proposal.id) if proposal else None,
        },
    )
    prop_read = _prop_read(proposal, app) if proposal is not None else None
    return _msg_read(msg), prop_read


async def list_messages(
    ctx: WorkspaceContext, *, application_id: uuid.UUID | None = None, limit: int = 50
) -> list[ResponseMessageRead]:
    q = (
        select(m.ResponseMessage)
        .where(m.ResponseMessage.workspace_id == ctx.workspace_id)
        .order_by(m.ResponseMessage.created_at.desc())
        .limit(min(limit, 100))
    )
    if application_id is not None:
        q = q.where(m.ResponseMessage.application_id == application_id)
    rows = list((await ctx.session.execute(q)).scalars())
    return [_msg_read(r) for r in rows]


async def list_proposals(
    ctx: WorkspaceContext, *, status: str = "pending"
) -> list[StatusProposalRead]:
    q = (
        select(m.StatusProposal, Application)
        .join(Application, Application.id == m.StatusProposal.application_id)
        .where(
            m.StatusProposal.workspace_id == ctx.workspace_id,
            m.StatusProposal.status == status,
        )
        .order_by(m.StatusProposal.created_at.desc())
        .limit(100)
    )
    rows = (await ctx.session.execute(q)).all()
    return [_prop_read(p, a) for p, a in rows]


async def decide_proposal(
    ctx: WorkspaceContext,
    proposal_id: uuid.UUID,
    *,
    accept: bool,
    note: str = "",
) -> StatusProposalRead:
    prop = await ctx.session.get(m.StatusProposal, proposal_id)
    if prop is None or prop.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Proposal not found", 404)
    if prop.status != "pending":
        raise AppError("conflict", "Proposal already decided", 409)

    app = await ctx.session.get(Application, prop.application_id)
    if app is None or app.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Application not found", 404)

    prop.status = "accepted" if accept else "rejected"
    prop.decided_at = datetime.now(UTC)

    if accept:
        await tracker.update_status(
            ctx,
            app.id,
            status=prop.to_status,
            note=note or prop.citation or prop.reason,
        )

    await audit.record(
        ctx,
        action="response.proposal_decided",
        target_type="status_proposal",
        target_id=str(prop.id),
        after={
            "accepted": accept,
            "to_status": prop.to_status,
            "application_id": str(prop.application_id),
        },
    )
    await ctx.session.flush()
    return _prop_read(prop, app)


async def batch_decide(
    ctx: WorkspaceContext,
    *,
    proposal_ids: list[uuid.UUID],
    accept: bool,
    note: str = "",
) -> list[StatusProposalRead]:
    out: list[StatusProposalRead] = []
    for pid in proposal_ids:
        out.append(await decide_proposal(ctx, pid, accept=accept, note=note))
    return out
