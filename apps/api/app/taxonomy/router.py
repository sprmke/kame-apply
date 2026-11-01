"""Taxonomy lookup endpoints (global read)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from app.core.security import WorkspaceContext, require_action
from app.taxonomy import normalize

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])
Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))


class OccupationHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    scheme: str
    code: str
    label: str
    score: float


class SkillHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw: str
    canonical: str
    skill_id: uuid.UUID | None
    score: float
    source: str


class BackfillResult(BaseModel):
    profile_id: str
    linked: int
    total: int


@router.get("/occupations/normalize", response_model=list[OccupationHit])
async def normalize_occupation(
    q: Annotated[str, Query(min_length=1, max_length=200)],
    ctx: WorkspaceContext = Read,
):
    hits = await normalize.normalize_title(ctx.session, q)
    return [
        OccupationHit(id=h.id, scheme=h.scheme, code=h.code, label=h.label, score=h.score)
        for h in hits
    ]


@router.get("/skills/normalize", response_model=SkillHit)
async def normalize_skill_route(
    q: Annotated[str, Query(min_length=1, max_length=120)],
    ctx: WorkspaceContext = Read,
):
    hit = await normalize.normalize_skill(ctx.session, q)
    return SkillHit(
        raw=hit.raw,
        canonical=hit.canonical,
        skill_id=hit.skill_id,
        score=hit.score,
        source=hit.source,
    )


@router.get("/occupations/{occupation_id}/adjacent", response_model=list[str])
async def adjacent_titles(occupation_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await normalize.suggest_adjacent_titles(ctx.session, occupation_id)


@router.post(
    "/profiles/{profile_id}/skills/backfill",
    response_model=BackfillResult,
)
async def backfill_skills(profile_id: uuid.UUID, ctx: WorkspaceContext = Write):
    result = await normalize.backfill_profile_skills(ctx, profile_id)
    return BackfillResult(**result)
