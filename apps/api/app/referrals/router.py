"""HTTP: contacts, matches, referral drafts, coach overview."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request

from app.core.security import WorkspaceContext, require_action
from app.referrals import parse as parsing
from app.referrals import schemas as s
from app.referrals import service

router = APIRouter(tags=["referrals"])

Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))


@router.post("/contacts/import", response_model=s.ContactImportResult)
async def import_contacts(body: s.ContactImportBody, ctx: WorkspaceContext = Write):
    return await service.import_contacts(ctx, body.contacts)


@router.post("/contacts/parse", response_model=s.ContactsParseRead)
async def parse_contacts(
    body: s.ContactsParseBody, request: Request, ctx: WorkspaceContext = Write
):
    result = await parsing.parse_contacts(
        ctx,
        request.app.state.settings,
        text=body.text,
        run_structured=getattr(request.app.state, "run_structured", None),
    )
    return s.ContactsParseRead(
        items=[s.ContactDraftRead.model_validate(item.model_dump()) for item in result["items"]],
        source=result["source"],
        ai_error=result["ai_error"],
    )


@router.get("/contacts", response_model=list[s.ContactRead])
async def list_contacts(q: str | None = None, ctx: WorkspaceContext = Read):
    return await service.list_contacts(ctx, q=q)


@router.get("/applications/{application_id}/referral-matches", response_model=list[s.MatchRead])
async def matches(application_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.matches_for_application(ctx, application_id)


@router.post(
    "/applications/{application_id}/referral-drafts",
    response_model=s.ReferralDraftRead,
)
async def create_draft(
    application_id: uuid.UUID, body: s.DraftCreateBody, ctx: WorkspaceContext = Write
):
    return await service.create_draft(ctx, application_id, body.contact_id)


@router.get(
    "/applications/{application_id}/referral-drafts",
    response_model=list[s.ReferralDraftRead],
)
async def list_drafts(application_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.list_drafts(ctx, application_id)


@router.get("/coach/profiles")
async def coach_profiles(ctx: WorkspaceContext = Read):
    return await service.coach_overview(ctx)
