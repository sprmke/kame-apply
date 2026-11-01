"""Document upload pipeline: validate → store in R2 → extract → sanitize → persist metadata.

LLM structuring into `documents.parsed` is slice 3. Audit rows store ids and codes only, never
file bytes or resume text.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from fastapi import UploadFile
from sqlalchemy import func, select

from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.core.storage import PRESIGN_GET_SECONDS, PRESIGN_PUT_SECONDS, ObjectStorage
from app.profiles import models as m
from app.profiles import schemas as s
from app.profiles.extract import (
    MAX_UPLOAD_BYTES,
    extract_text,
    scan_bytes,
    validate_upload,
)
from app.profiles.sanitize import sanitize_untrusted_text
from app.profiles.service import _get_profile
from app.workspaces import limits as workspace_limits

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _object_key(
    workspace_id: uuid.UUID, profile_id: uuid.UUID, doc_id: uuid.UUID, filename: str
) -> str:
    safe = _SAFE_NAME.sub("_", filename).strip("._") or "upload"
    if len(safe) > 180:
        safe = safe[:180]
    return f"ws/{workspace_id}/profiles/{profile_id}/documents/{doc_id}/{safe}"


def _warnings_from_sanitize(
    *,
    stripped_kinds: tuple[str, ...],
    injection_lines_removed: int,
    ocr_needed: bool,
) -> list[dict[str, str]]:
    warnings: list[dict[str, str]] = []
    if stripped_kinds:
        warnings.append(
            {
                "code": "sensitive_numbers_stripped",
                "message": "Sensitive-looking numbers were removed from the extracted text",
            }
        )
    if injection_lines_removed:
        warnings.append(
            {
                "code": "injection_lines_removed",
                "message": "Instruction-shaped lines were removed from the extracted text",
            }
        )
    if ocr_needed:
        warnings.append(
            {
                "code": "needs_ocr",
                "message": "Little or no text layer found; upload a DOCX or a text PDF if you can",
            }
        )
    return warnings


async def _storage_used_bytes(ctx: WorkspaceContext) -> int:
    total = (
        await ctx.session.execute(select(func.coalesce(func.sum(m.Document.size_bytes), 0)))
    ).scalar_one()
    return int(total)


async def _require_storage_room(ctx: WorkspaceContext, extra_bytes: int) -> None:
    caps = await workspace_limits.get_limits(ctx.session, ctx.workspace_id)
    used = await _storage_used_bytes(ctx)
    cap_bytes = caps["max_storage_mb"] * 1024 * 1024
    if used + extra_bytes > cap_bytes:
        raise AppError(
            "storage_limit",
            "Workspace storage limit reached",
            409,
            {"limit": "max_storage_mb", "cap_mb": caps["max_storage_mb"]},
        )


async def _get_document(
    ctx: WorkspaceContext, profile_id: uuid.UUID, document_id: uuid.UUID
) -> m.Document:
    await _get_profile(ctx, profile_id)
    row = await ctx.session.get(m.Document, document_id)
    if row is None or row.profile_id != profile_id or row.workspace_id != ctx.workspace_id:
        raise AppError("document_not_found", "Document not found", 404)
    return row


async def list_documents(ctx: WorkspaceContext, profile_id: uuid.UUID) -> list[m.Document]:
    await _get_profile(ctx, profile_id)
    q = (
        select(m.Document)
        .where(m.Document.profile_id == profile_id)
        .order_by(m.Document.created_at.desc())
    )
    return list((await ctx.session.execute(q)).scalars())


async def get_document(
    ctx: WorkspaceContext, profile_id: uuid.UUID, document_id: uuid.UUID
) -> m.Document:
    return await _get_document(ctx, profile_id, document_id)


async def _process_bytes(
    ctx: WorkspaceContext,
    row: m.Document,
    data: bytes,
    mime: str,
    storage: ObjectStorage,
) -> m.Document:
    scan_bytes(data)
    try:
        extracted = extract_text(data, mime)
        cleaned = sanitize_untrusted_text(extracted.text)
        row.extracted_text = cleaned.text
        row.ocr_used = extracted.ocr_needed
        row.warnings = _warnings_from_sanitize(
            stripped_kinds=cleaned.stripped_kinds,
            injection_lines_removed=cleaned.injection_lines_removed,
            ocr_needed=extracted.ocr_needed,
        )
        row.status = "ready"
        row.mime = mime
        row.size_bytes = len(data)
    except AppError:
        row.status = "failed"
        row.warnings = [{"code": "extract_failed", "message": "Could not read this file"}]
        await ctx.session.flush()
        raise
    except Exception:
        row.status = "failed"
        row.warnings = [{"code": "extract_failed", "message": "Could not read this file"}]
        await ctx.session.flush()
        await audit.record(
            ctx,
            action="document.failed",
            target_type="document",
            target_id=str(row.id),
            after={"profile_id": str(row.profile_id), "code": "extract_failed"},
        )
        raise AppError("extract_failed", "Could not read this file", 422) from None

    await storage.put(row.r2_key, data, mime)
    await ctx.session.flush()
    await ctx.session.refresh(row)
    await audit.record(
        ctx,
        action="document.ready",
        target_type="document",
        target_id=str(row.id),
        after={
            "profile_id": str(row.profile_id),
            "kind": row.kind,
            "mime": row.mime,
            "size_bytes": row.size_bytes,
            "warning_codes": [w["code"] for w in row.warnings],
            "ocr_used": row.ocr_used,
        },
    )
    return row


async def upload_document(
    ctx: WorkspaceContext,
    profile_id: uuid.UUID,
    file: UploadFile,
    storage: ObjectStorage,
    *,
    kind: s.DocumentKind = "resume_upload",
) -> m.Document:
    await _get_profile(ctx, profile_id)
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise AppError(
            "file_too_large",
            "File must be 10 MB or smaller",
            422,
            {"max_bytes": MAX_UPLOAD_BYTES},
        )
    filename = file.filename or "upload.txt"
    mime = validate_upload(filename, len(data), file.content_type)
    await _require_storage_room(ctx, len(data))

    doc_id = uuid.uuid4()
    key = _object_key(ctx.workspace_id, profile_id, doc_id, filename)
    row = m.Document(
        id=doc_id,
        workspace_id=ctx.workspace_id,
        profile_id=profile_id,
        kind=kind,
        r2_key=key,
        filename=filename[:260],
        mime=mime,
        size_bytes=len(data),
        status="pending",
        created_by=ctx.user_id,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="document.created",
        target_type="document",
        target_id=str(row.id),
        after={"profile_id": str(profile_id), "kind": kind, "mime": mime},
    )
    return await _process_bytes(ctx, row, data, mime, storage)


async def presign_upload(
    ctx: WorkspaceContext,
    profile_id: uuid.UUID,
    body: s.DocumentPresign,
    storage: ObjectStorage,
) -> dict[str, Any]:
    await _get_profile(ctx, profile_id)
    mime = validate_upload(body.filename, body.size_bytes, body.content_type)
    await _require_storage_room(ctx, body.size_bytes)

    doc_id = uuid.uuid4()
    key = _object_key(ctx.workspace_id, profile_id, doc_id, body.filename)
    row = m.Document(
        id=doc_id,
        workspace_id=ctx.workspace_id,
        profile_id=profile_id,
        kind=body.kind,
        r2_key=key,
        filename=body.filename[:260],
        mime=mime,
        size_bytes=body.size_bytes,
        status="pending",
        created_by=ctx.user_id,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    url = await storage.presign_put(key, mime)
    await audit.record(
        ctx,
        action="document.created",
        target_type="document",
        target_id=str(row.id),
        after={"profile_id": str(profile_id), "kind": body.kind, "mime": mime, "presign": True},
    )
    return {
        "document_id": row.id,
        "upload_url": url,
        "r2_key": key,
        "expires_in": PRESIGN_PUT_SECONDS,
    }


async def finalize_document(
    ctx: WorkspaceContext,
    profile_id: uuid.UUID,
    document_id: uuid.UUID,
    storage: ObjectStorage,
) -> m.Document:
    row = await _get_document(ctx, profile_id, document_id)
    if row.status == "ready":
        return row
    data = await storage.get(row.r2_key)
    size = len(data)
    if size > MAX_UPLOAD_BYTES:
        row.status = "failed"
        row.warnings = [{"code": "file_too_large", "message": "File must be 10 MB or smaller"}]
        await ctx.session.flush()
        raise AppError("file_too_large", "File must be 10 MB or smaller", 422)
    mime = validate_upload(row.filename, size, row.mime)
    # Re-check room against actual size (presign used the declared size).
    used = await _storage_used_bytes(ctx)
    caps = await workspace_limits.get_limits(ctx.session, ctx.workspace_id)
    # Subtract this row's reserved size then add actual.
    adjusted = used - row.size_bytes + size
    if adjusted > caps["max_storage_mb"] * 1024 * 1024:
        raise AppError("storage_limit", "Workspace storage limit reached", 409)
    # put is a no-op overwrite when bytes are already at the key; keeps MemoryStorage consistent.
    return await _process_bytes(ctx, row, data, mime, storage)


async def download_url(
    ctx: WorkspaceContext,
    profile_id: uuid.UUID,
    document_id: uuid.UUID,
    storage: ObjectStorage,
) -> dict[str, Any]:
    row = await _get_document(ctx, profile_id, document_id)
    url = await storage.presign_get(row.r2_key)
    return {"download_url": url, "expires_in": PRESIGN_GET_SECONDS}


async def delete_document(
    ctx: WorkspaceContext,
    profile_id: uuid.UUID,
    document_id: uuid.UUID,
    storage: ObjectStorage,
) -> None:
    row = await _get_document(ctx, profile_id, document_id)
    key = row.r2_key
    await ctx.session.delete(row)
    await ctx.session.flush()
    await storage.delete(key)
    await audit.record(
        ctx,
        action="document.deleted",
        target_type="document",
        target_id=str(document_id),
        after={"profile_id": str(profile_id)},
    )
