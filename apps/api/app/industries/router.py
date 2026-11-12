"""HTTP surface for industry packs, workspace fields, and the experience manifest."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.errors import AppError
from app.core.security import Principal, WorkspaceContext, current_principal, require_action
from app.industries import schemas as s
from app.industries import service
from app.industries.detect import detect_industry, draft_custom_pack
from app.industries.registry import list_packs

router = APIRouter(prefix="/industries", tags=["industries"])
workspace_router = APIRouter(prefix="/workspace", tags=["industries"])
workspaces_router = APIRouter(prefix="/workspaces", tags=["industries"])
Read = Depends(require_action("data.read"))
Write = Depends(require_action("workspace.update"))


@router.get("", response_model=s.IndustryList)
async def list_industries(_: Principal = Depends(current_principal)):
    return s.IndustryList(
        items=[
            s.IndustrySummary(
                key=pack.key,
                label_key=pack.label_key,
                icon=pack.icon,
                role_families=[
                    s.RoleFamilyRead(
                        key=family.key, label_key=family.label_key, titles=list(family.titles)
                    )
                    for family in pack.role_families
                ],
            )
            for pack in list_packs()
        ]
    )


@router.post("/detect", response_model=s.IndustryDetectRead)
async def detect(body: s.IndustryDetectIn, _: Principal = Depends(current_principal)):
    result = detect_industry(body.text)
    return s.IndustryDetectRead(
        pack_key=result.pack_key,
        role_family=result.role_family,
        confidence=result.confidence,
        reasons=result.reasons,
    )


@router.post("/draft", response_model=s.CustomPackDraftRead)
async def draft_pack(body: s.CustomPackDraftIn, _: Principal = Depends(current_principal)):
    return s.CustomPackDraftRead(**draft_custom_pack(body.description, base_pack=body.base_pack))


@workspace_router.post("/industries/custom", response_model=s.WorkspaceIndustryList)
async def add_custom_pack(body: s.CustomPackAcceptIn, ctx: WorkspaceContext = Write):
    items = await service.add_custom_industry(ctx, key=body.key, pack_data=body.pack)
    return s.WorkspaceIndustryList(items=[s.WorkspaceIndustryRead(**item) for item in items])


@workspace_router.get("/experience", response_model=s.IndustryExperienceRead)
async def get_experience(ctx: WorkspaceContext = Read):
    return s.IndustryExperienceRead(**await service.get_experience(ctx))


@workspaces_router.get("/{workspace_id}/experience", response_model=s.IndustryExperienceRead)
async def get_experience_for(workspace_id: uuid.UUID, ctx: WorkspaceContext = Read):
    # The path id is only a locator; the active workspace still comes from the verified header.
    if workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Workspace not found", 404)
    return s.IndustryExperienceRead(**await service.get_experience(ctx))


@workspace_router.get("/industries", response_model=s.WorkspaceIndustryList)
async def list_workspace_industries(ctx: WorkspaceContext = Read):
    return s.WorkspaceIndustryList(
        items=[s.WorkspaceIndustryRead(**item) for item in await service.list_for_workspace(ctx)]
    )


@workspace_router.post("/industries", response_model=s.WorkspaceIndustryList)
async def add_workspace_industry(body: s.IndustryAdd, ctx: WorkspaceContext = Write):
    items = await service.add_industry(ctx, body.key, is_primary=body.is_primary)
    return s.WorkspaceIndustryList(items=[s.WorkspaceIndustryRead(**item) for item in items])


@workspace_router.put("/industries/primary", response_model=s.WorkspaceIndustryList)
async def set_primary_industry(body: s.IndustryPrimaryIn, ctx: WorkspaceContext = Write):
    items = await service.set_primary(ctx, body.key)
    return s.WorkspaceIndustryList(items=[s.WorkspaceIndustryRead(**item) for item in items])


@workspace_router.delete("/industries/{key}", response_model=s.WorkspaceIndustryList)
async def remove_workspace_industry(key: str, ctx: WorkspaceContext = Write):
    items = await service.remove_industry(ctx, key)
    return s.WorkspaceIndustryList(items=[s.WorkspaceIndustryRead(**item) for item in items])
