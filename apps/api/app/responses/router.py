"""HTTP: recruiter response tracking."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.core.security import WorkspaceContext, require_action
from app.responses import schemas as s
from app.responses import service

router = APIRouter(tags=["responses"])

Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))


@router.post("/responses/ingest")
async def ingest(body: s.IngestReplyBody, ctx: WorkspaceContext = Write):
    msg, proposal = await service.ingest_reply(
        ctx,
        application_id=body.application_id,
        sender=body.sender,
        subject=body.subject,
        body_text=body.body_text,
    )
    return {"message": msg, "proposal": proposal}


@router.get("/responses", response_model=list[s.ResponseMessageRead])
async def list_responses(
    application_id: uuid.UUID | None = None,
    ctx: WorkspaceContext = Read,
):
    return await service.list_messages(ctx, application_id=application_id)


@router.get("/responses/proposals", response_model=list[s.StatusProposalRead])
async def list_proposals(
    status: str = Query(default="pending"),
    ctx: WorkspaceContext = Read,
):
    return await service.list_proposals(ctx, status=status)


@router.post("/responses/proposals/{proposal_id}/decide", response_model=s.StatusProposalRead)
async def decide(
    proposal_id: uuid.UUID,
    body: s.DecideProposalBody,
    ctx: WorkspaceContext = Write,
):
    return await service.decide_proposal(ctx, proposal_id, accept=body.accept, note=body.note)


@router.post("/responses/proposals/batch", response_model=list[s.StatusProposalRead])
async def batch(body: s.BatchDecideBody, ctx: WorkspaceContext = Write):
    return await service.batch_decide(
        ctx, proposal_ids=body.proposal_ids, accept=body.accept, note=body.note
    )
