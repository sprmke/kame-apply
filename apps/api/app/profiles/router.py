import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.core.security import WorkspaceContext, require_action
from app.profiles import answers as answers_svc
from app.profiles import documents as docs
from app.profiles import interview as interview_svc
from app.profiles import merge as merge_svc
from app.profiles import parse as parse_svc
from app.profiles import schemas as s
from app.profiles import service
from app.profiles import voice as voice_svc

router = APIRouter(prefix="/profiles", tags=["profiles"])

Read = Depends(require_action("data.read"))
Write = Depends(require_action("data.write"))
Upload = Annotated[UploadFile, File()]
DocKind = Annotated[
    Literal["resume_upload", "portfolio", "generated", "paste"],
    Form(),
]


@router.get("", response_model=list[s.ProfileRead])
async def list_profiles(ctx: WorkspaceContext = Read):
    return await service.list_profiles(ctx)


@router.post("", response_model=s.ProfileRead, status_code=201)
async def create_profile(body: s.ProfileCreate, ctx: WorkspaceContext = Write):
    return await service.create_profile(ctx, body)


@router.get("/{profile_id}", response_model=s.ProfileFull)
async def get_profile(profile_id: uuid.UUID, ctx: WorkspaceContext = Read):
    data = await service.full_profile(ctx, profile_id)
    profile = data.pop("profile")
    return {**s.ProfileRead.model_validate(profile).model_dump(), **data}


@router.patch("/{profile_id}", response_model=s.ProfileRead)
async def update_profile(
    profile_id: uuid.UUID, body: s.ProfileUpdate, ctx: WorkspaceContext = Write
):
    return await service.update_profile(ctx, profile_id, body)


@router.delete("/{profile_id}", response_model=s.OkRead)
async def delete_profile(profile_id: uuid.UUID, ctx: WorkspaceContext = Write):
    await service.delete_profile(ctx, profile_id)
    return s.OkRead()


def _mount(key: str) -> None:
    """One list/create/update/delete quartet per fact section, with typed bodies and responses."""
    sec = service.SECTIONS[key]
    singular = key.rstrip("s") if key != "education" else "education"

    async def list_items(profile_id: uuid.UUID, ctx: WorkspaceContext = Read) -> list[Any]:
        return await service.list_section(ctx, profile_id, key)

    async def create_item(
        profile_id: uuid.UUID,
        body: sec.create,  # pyright: ignore[reportInvalidTypeForm]
        ctx: WorkspaceContext = Write,
    ) -> Any:
        return await service.create_item(ctx, profile_id, key, body)

    async def update_item(
        profile_id: uuid.UUID,
        item_id: uuid.UUID,
        body: sec.patch,  # pyright: ignore[reportInvalidTypeForm]
        ctx: WorkspaceContext = Write,
    ) -> Any:
        return await service.update_item(ctx, profile_id, key, item_id, body)

    async def delete_item(profile_id: uuid.UUID, item_id: uuid.UUID, ctx: WorkspaceContext = Write):
        await service.delete_item(ctx, profile_id, key, item_id)
        return s.OkRead()

    path = f"/{{profile_id}}/{key}"
    router.add_api_route(
        path,
        list_items,
        methods=["GET"],
        response_model=list[sec.read],
        name=f"list_{key}",
        operation_id=f"list_profile_{key}",
    )
    router.add_api_route(
        path,
        create_item,
        methods=["POST"],
        response_model=sec.read,
        status_code=201,
        name=f"create_{singular}",
        operation_id=f"create_profile_{singular}",
    )
    router.add_api_route(
        path + "/{item_id}",
        update_item,
        methods=["PATCH"],
        response_model=sec.read,
        name=f"update_{singular}",
        operation_id=f"update_profile_{singular}",
    )
    router.add_api_route(
        path + "/{item_id}",
        delete_item,
        methods=["DELETE"],
        response_model=s.OkRead,
        name=f"delete_{singular}",
        operation_id=f"delete_profile_{singular}",
    )


for _key in service.SECTIONS:
    _mount(_key)


# ---- answer bank -----------------------------------------------------------------------------


@router.get("/{profile_id}/answers/keys", response_model=list[s.CanonicalKeyRead])
async def list_answer_keys(profile_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await answers_svc.list_canonical_keys(ctx, profile_id)


@router.get("/{profile_id}/answers", response_model=list[s.AnswerRead])
async def list_answers(
    profile_id: uuid.UUID,
    key: str | None = None,
    scope: s.AnswerScope | None = None,
    country: str | None = None,
    track_id: uuid.UUID | None = None,
    approved: bool | None = None,
    q: str | None = None,
    ctx: WorkspaceContext = Read,
):
    return await answers_svc.list_answers(
        ctx,
        profile_id,
        key=key,
        scope=scope,
        country=country,
        track_id=track_id,
        approved=approved,
        q=q,
    )


@router.post("/{profile_id}/answers", response_model=s.AnswerRead, status_code=201)
async def create_answer(profile_id: uuid.UUID, body: s.AnswerCreate, ctx: WorkspaceContext = Write):
    return await answers_svc.create_answer(ctx, profile_id, body)


@router.post("/{profile_id}/answers/setup", response_model=s.AnswerSetupRead)
async def setup_answers(profile_id: uuid.UUID, body: s.AnswerSetup, ctx: WorkspaceContext = Write):
    return await answers_svc.setup_answers(ctx, profile_id, body)


@router.get("/{profile_id}/answers/{answer_id}", response_model=s.AnswerRead)
async def get_answer(profile_id: uuid.UUID, answer_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await answers_svc.get_answer(ctx, profile_id, answer_id)


@router.patch("/{profile_id}/answers/{answer_id}", response_model=s.AnswerRead)
async def update_answer(
    profile_id: uuid.UUID,
    answer_id: uuid.UUID,
    body: s.AnswerUpdate,
    ctx: WorkspaceContext = Write,
):
    return await answers_svc.update_answer(ctx, profile_id, answer_id, body)


@router.delete("/{profile_id}/answers/{answer_id}", response_model=s.OkRead)
async def delete_answer(profile_id: uuid.UUID, answer_id: uuid.UUID, ctx: WorkspaceContext = Write):
    await answers_svc.delete_answer(ctx, profile_id, answer_id)
    return s.OkRead()


# ---- interview -------------------------------------------------------------------------------


@router.get("/{profile_id}/interview/gaps", response_model=list[s.InterviewGapRead])
async def list_interview_gaps(profile_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await interview_svc.list_gaps(ctx, profile_id)


@router.get("/{profile_id}/interview/stream")
async def stream_interview_question(profile_id: uuid.UUID, ctx: WorkspaceContext = Read):
    frames = await interview_svc.prepare_question_stream(ctx, profile_id)
    return StreamingResponse(
        interview_svc.iter_frames(frames),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{profile_id}/interview/turns", response_model=s.InterviewTurnRead, status_code=201)
async def interview_turn(
    profile_id: uuid.UUID, body: s.InterviewTurn, ctx: WorkspaceContext = Write
):
    return await interview_svc.create_turn(ctx, profile_id, body)


@router.get("/{profile_id}/interview/proposals", response_model=list[s.ProposalRead])
async def list_interview_proposals(
    profile_id: uuid.UUID,
    status: s.ProposalStatus | None = "pending",
    ctx: WorkspaceContext = Read,
):
    return await interview_svc.list_proposals(ctx, profile_id, status=status)


@router.post(
    "/{profile_id}/interview/proposals/{proposal_id}/accept",
    response_model=s.ProposalRead,
)
async def accept_interview_proposal(
    profile_id: uuid.UUID, proposal_id: uuid.UUID, ctx: WorkspaceContext = Write
):
    return await interview_svc.accept_proposal(ctx, profile_id, proposal_id)


@router.post(
    "/{profile_id}/interview/proposals/{proposal_id}/reject",
    response_model=s.ProposalRead,
)
async def reject_interview_proposal(
    profile_id: uuid.UUID, proposal_id: uuid.UUID, ctx: WorkspaceContext = Write
):
    return await interview_svc.reject_proposal(ctx, profile_id, proposal_id)


# ---- voice profile ---------------------------------------------------------------------------


@router.get("/{profile_id}/voice", response_model=s.VoiceRead)
async def get_voice(profile_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await voice_svc.get_voice(ctx, profile_id)


@router.put("/{profile_id}/voice/samples", response_model=s.VoiceRead)
async def put_voice_samples(
    profile_id: uuid.UUID, body: s.VoiceSamplesPut, ctx: WorkspaceContext = Write
):
    return await voice_svc.put_samples(ctx, profile_id, body)


@router.post("/{profile_id}/voice/analyze", response_model=s.VoiceRead)
async def analyze_voice(profile_id: uuid.UUID, ctx: WorkspaceContext = Write):
    return await voice_svc.analyze_voice(ctx, profile_id)


@router.patch("/{profile_id}/voice", response_model=s.VoiceRead)
async def update_voice(profile_id: uuid.UUID, body: s.VoiceUpdate, ctx: WorkspaceContext = Write):
    return await voice_svc.update_voice(ctx, profile_id, body)


# ---- documents (upload pipeline; LLM parse is slice 3) ---------------------------------------


@router.get("/{profile_id}/documents", response_model=list[s.DocumentListItem])
async def list_documents(profile_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await docs.list_documents(ctx, profile_id)


@router.post("/{profile_id}/documents", response_model=s.DocumentRead, status_code=201)
async def upload_document(
    profile_id: uuid.UUID,
    request: Request,
    file: Upload,
    kind: DocKind = "resume_upload",
    ctx: WorkspaceContext = Write,
):
    return await docs.upload_document(ctx, profile_id, file, request.app.state.storage, kind=kind)


@router.post(
    "/{profile_id}/documents/presign",
    response_model=s.DocumentPresignRead,
    status_code=201,
)
async def presign_document(
    profile_id: uuid.UUID,
    body: s.DocumentPresign,
    request: Request,
    ctx: WorkspaceContext = Write,
):
    return await docs.presign_upload(ctx, profile_id, body, request.app.state.storage)


@router.post(
    "/{profile_id}/documents/{document_id}/finalize",
    response_model=s.DocumentRead,
)
async def finalize_document(
    profile_id: uuid.UUID,
    document_id: uuid.UUID,
    request: Request,
    ctx: WorkspaceContext = Write,
):
    return await docs.finalize_document(ctx, profile_id, document_id, request.app.state.storage)


@router.get("/{profile_id}/documents/{document_id}", response_model=s.DocumentRead)
async def get_document(profile_id: uuid.UUID, document_id: uuid.UUID, ctx: WorkspaceContext = Read):
    return await docs.get_document(ctx, profile_id, document_id)


@router.get(
    "/{profile_id}/documents/{document_id}/download-url",
    response_model=s.DocumentDownloadRead,
)
async def document_download_url(
    profile_id: uuid.UUID,
    document_id: uuid.UUID,
    request: Request,
    ctx: WorkspaceContext = Read,
):
    return await docs.download_url(ctx, profile_id, document_id, request.app.state.storage)


@router.delete("/{profile_id}/documents/{document_id}", response_model=s.OkRead)
async def delete_document(
    profile_id: uuid.UUID,
    document_id: uuid.UUID,
    request: Request,
    ctx: WorkspaceContext = Write,
):
    await docs.delete_document(ctx, profile_id, document_id, request.app.state.storage)
    return s.OkRead()


@router.post("/{profile_id}/documents/{document_id}/parse", response_model=s.DocumentRead)
async def parse_document(
    profile_id: uuid.UUID,
    document_id: uuid.UUID,
    request: Request,
    ctx: WorkspaceContext = Write,
):
    kwargs: dict[str, Any] = {}
    factory = getattr(request.app.state, "model_factory", None)
    if factory is not None:
        kwargs["model_factory"] = factory
    runner = getattr(request.app.state, "run_structured", None)
    if runner is not None:
        kwargs["run_structured"] = runner
    return await parse_svc.parse_document(
        ctx, request.app.state.settings, profile_id, document_id, **kwargs
    )


@router.post(
    "/{profile_id}/documents/{document_id}/confirm",
    response_model=s.DocumentConfirmRead,
)
async def confirm_document(
    profile_id: uuid.UUID,
    document_id: uuid.UUID,
    body: s.DocumentConfirm,
    ctx: WorkspaceContext = Write,
):
    return await parse_svc.confirm_document(ctx, profile_id, document_id, body)


@router.get("/{profile_id}/documents/{document_id}/merge", response_model=dict)
async def merge_preview(
    profile_id: uuid.UUID, document_id: uuid.UUID, ctx: WorkspaceContext = Read
):
    return await merge_svc.build_merge_preview(ctx, profile_id, document_id)


@router.post(
    "/{profile_id}/documents/{document_id}/merge",
    response_model=s.MergeResolveRead,
)
async def merge_resolve(
    profile_id: uuid.UUID,
    document_id: uuid.UUID,
    body: s.MergeResolve,
    ctx: WorkspaceContext = Write,
):
    return await merge_svc.resolve_merge(ctx, profile_id, document_id, body)
