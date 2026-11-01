"""Answer Desk HTTP API (also used by extension / runner later)."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.answers import restriction as restr
from app.answers import schemas as s
from app.answers import service
from app.core.security import WorkspaceContext, require_action

router = APIRouter(tags=["answer-desk"])

Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))


@router.post("/answer-desk/detect", response_model=s.RestrictionRead)
async def detect_restriction(body: s.RestrictionProbe, ctx: WorkspaceContext = Read):
    hit = restr.detect_ai_restriction(body.text, page_context=body.page_context)
    return s.RestrictionRead(
        restricted=hit.restricted,
        page_level=hit.page_level,
        matched=hit.matched,
        score=hit.score,
    )


@router.post("/answer-desk/parse", response_model=s.SessionRead, status_code=201)
async def parse_desk(body: s.ParseBody, ctx: WorkspaceContext = Write):
    return await service.parse_and_draft(ctx, body)


@router.get("/answer-desk/sessions/{session_id}", response_model=s.SessionRead)
async def get_session(session_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.get_session(ctx, session_id)


@router.post("/answer-desk/parse/stream")
async def parse_desk_stream(body: s.ParseBody, ctx: WorkspaceContext = Write):
    """SSE: session meta first, then each item as it is ready (same resolver as parse)."""
    session = await service.parse_and_draft(ctx, body)

    async def gen():
        meta = {
            "id": str(session["id"]),
            "profile_id": str(session["profile_id"]),
            "application_id": str(session["application_id"])
            if session.get("application_id")
            else None,
            "page_restricted": session.get("page_restricted"),
            "count": len(session.get("items") or []),
        }
        yield f"event: session\ndata: {json.dumps(meta)}\n\n"
        for item in session.get("items") or []:
            payload = {
                **item,
                "id": str(item["id"]),
                "session_id": str(item["session_id"]),
                "answer_bank_id": str(item["answer_bank_id"])
                if item.get("answer_bank_id")
                else None,
            }
            yield f"event: item\ndata: {json.dumps(payload, default=str)}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/answer-desk/items/{item_id}/tone", response_model=s.ItemRead)
async def tone_item(item_id: uuid.UUID, body: s.ToneBody, ctx: WorkspaceContext = Write):
    return await service.redraft_item(ctx, item_id, tone=body.tone)


@router.patch("/answer-desk/items/{item_id}", response_model=s.ItemRead)
async def patch_item(item_id: uuid.UUID, body: s.ItemPatch, ctx: WorkspaceContext = Write):
    return await service.patch_item(ctx, item_id, body.draft)


@router.post("/answer-desk/items/{item_id}/save-to-bank", response_model=s.ItemRead)
async def save_bank(
    item_id: uuid.UUID, body: s.SaveBankBody | None = None, ctx: WorkspaceContext = Write
):
    body = body or s.SaveBankBody()
    return await service.save_to_bank(ctx, item_id, key=body.key, approve=body.approve)


@router.get("/applications/{application_id}/answers", response_model=list[s.ItemRead])
async def application_answers(application_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await service.list_for_application(ctx, application_id)


@router.put("/profiles/{profile_id}/ai-use-stance")
async def put_stance(profile_id: uuid.UUID, body: s.StanceBody, ctx: WorkspaceContext = Write):
    return await service.set_ai_stance(ctx, profile_id, body.ai_use_stance)
