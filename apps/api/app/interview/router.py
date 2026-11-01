"""HTTP: interview prep."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.errors import AppError
from app.core.security import WorkspaceContext, require_action
from app.interview import schemas as s
from app.interview import service

router = APIRouter(tags=["interview"])

Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))


@router.get(
    "/applications/{application_id}/interview-prep",
    response_model=s.InterviewPrepRead,
)
async def get_prep(application_id: uuid.UUID, ctx: WorkspaceContext = Read):
    row = await service.get_prep(ctx, application_id)
    if row is None:
        raise AppError("not_found", "Interview prep not found", 404)
    return row


@router.post(
    "/applications/{application_id}/interview-prep",
    response_model=s.InterviewPrepRead,
)
async def generate_prep(application_id: uuid.UUID, ctx: WorkspaceContext = Write):
    return await service.generate_prep(ctx, application_id)
