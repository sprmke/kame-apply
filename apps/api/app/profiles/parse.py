"""Resume parse (LLM draft) and confirm (write draft into profile tables).

Draft semantics: `documents.parsed` is never applied until confirm. Confirm is one transaction
and sets `source=parsed` on every new fact. Merge/dedupe of a second resume is slice 4.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from pydantic_ai import PromptedOutput

from app.ai import prompts as prompt_registry
from app.ai import service as ai
from app.audit import service as audit
from app.core.config import Settings
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.profiles import models as m
from app.profiles import schemas as s
from app.profiles.documents import _get_document
from app.profiles.parse_schema import LOW_CONFIDENCE, ProfileExtract
from app.profiles.sanitize import sanitize_untrusted_text
from app.profiles.service import _get_profile, evidence_strength, profile_has_facts

PROMPT = prompt_registry.PROFILE_EXTRACT
FEATURE = "profile_extract"
TIER = "standard"
MAX_PARSE_CHARS = 60_000
PARSE_MAX_OUTPUT_TOKENS = 8192

StructuredRunner = Callable[..., Awaitable[ai.StructuredAiResult]]


def _delimit_resume(text: str) -> str:
    return (
        "Extract a ProfileExtract JSON object from this resume.\n\n"
        "<<<UNTRUSTED_RESUME_TEXT>>>\n"
        f"{text}\n"
        "<<<END_UNTRUSTED_RESUME_TEXT>>>"
    )


def _scrub_str(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = sanitize_untrusted_text(value).text
    return cleaned or None


def post_process_draft(draft: ProfileExtract) -> ProfileExtract:
    """Second-pass sanitize so model output cannot reintroduce sensitive numbers or injection."""
    data = draft.model_dump()
    for key in ("display_name", "headline", "summary", "location", "timezone", "language"):
        field = data[key]
        field["value"] = _scrub_str(field.get("value"))
        field["span"] = _scrub_str(field.get("span"))
    for link in data["links"]:
        link["label"] = (_scrub_str(link.get("label")) or link.get("label") or "link")[:80]
        link["url"] = (_scrub_str(link.get("url")) or link.get("url") or "")[:500]
    data["links"] = [lk for lk in data["links"] if lk.get("url")]

    def _scrub_item(item: dict[str, Any], text_keys: tuple[str, ...]) -> dict[str, Any]:
        for k in text_keys:
            if k in item and isinstance(item[k], str):
                item[k] = _scrub_str(item[k]) or item[k]
        if "span" in item:
            item["span"] = _scrub_str(item.get("span"))
        for b in item.get("bullets") or []:
            b["text"] = _scrub_str(b.get("text")) or b.get("text") or ""
            b["span"] = _scrub_str(b.get("span"))
            b["skills"] = [(_scrub_str(x) or x)[:80] for x in (b.get("skills") or []) if x]
        if "bullets" in item:
            item["bullets"] = [b for b in item["bullets"] if b.get("text")]
        return item

    data["experiences"] = [
        _scrub_item(e, ("company", "title", "employment_type", "location", "description"))
        for e in data["experiences"]
        if e.get("company") and e.get("title")
    ]
    data["projects"] = [
        _scrub_item(p, ("name", "url", "description")) for p in data["projects"] if p.get("name")
    ]
    data["education"] = [
        _scrub_item(e, ("institution", "degree", "field", "notes"))
        for e in data["education"]
        if e.get("institution")
    ]
    data["certifications"] = [
        _scrub_item(c, ("name", "issuer", "jurisdiction"))
        for c in data["certifications"]
        if c.get("name")
    ]
    data["languages"] = [
        _scrub_item(lang, ("name", "proficiency")) for lang in data["languages"] if lang.get("name")
    ]
    data["skills"] = [_scrub_item(sk, ("name", "level")) for sk in data["skills"] if sk.get("name")]
    return ProfileExtract.model_validate(data)


def _quality(
    draft: ProfileExtract,
    *,
    provider: str,
    model: str,
    truncated: bool,
    confirmed_at: str | None = None,
) -> dict[str, Any]:
    low = draft.low_confidence_paths()
    return {
        "prompt_version": PROMPT.key,
        "provider": provider,
        "model": model,
        "truncated": truncated,
        "low_confidence_paths": low,
        "low_confidence_count": len(low),
        "threshold": LOW_CONFIDENCE,
        "confirmed_at": confirmed_at,
    }


def _assert_ready_for_parse(row: m.Document) -> None:
    if row.status != "ready":
        raise AppError("document_not_ready", "Document is not ready to parse", 422)
    if not (row.extracted_text and row.extracted_text.strip()):
        raise AppError(
            "empty_extract",
            "No text could be extracted from this document",
            422,
        )
    quality = row.parse_quality or {}
    if quality.get("confirmed_at"):
        raise AppError(
            "document_already_confirmed",
            "This document was already confirmed; upload a new file to parse again",
            409,
        )


async def parse_document(
    ctx: WorkspaceContext,
    settings: Settings,
    profile_id: uuid.UUID,
    document_id: uuid.UUID,
    *,
    model_factory=None,
    run_structured: StructuredRunner | None = None,
) -> m.Document:
    await _get_profile(ctx, profile_id)
    row = await _get_document(ctx, profile_id, document_id)
    _assert_ready_for_parse(row)

    text = row.extracted_text or ""
    truncated = len(text) > MAX_PARSE_CHARS
    if truncated:
        text = text[:MAX_PARSE_CHARS]

    runner = run_structured or ai.run_structured
    # PromptedOutput: Gemini rejects NativeOutput for ProfileExtract ("too many states"
    # from nested max_length / date / Decimal bounds). Prompted JSON still validates as ProfileExtract.

    kwargs: dict[str, Any] = {
        "tier": TIER,
        "feature": FEATURE,
        "system": PROMPT.system,
        "prompt": _delimit_resume(text),
        "output_type": PromptedOutput(ProfileExtract),
        "max_output_tokens": PARSE_MAX_OUTPUT_TOKENS,
    }
    if model_factory is not None:
        kwargs["model_factory"] = model_factory
    result = await runner(ctx, settings, **kwargs)
    draft = post_process_draft(result.output)
    row.parsed = draft.model_dump(mode="json")
    row.parse_quality = _quality(
        draft, provider=result.provider, model=result.model, truncated=truncated
    )
    # Surface truncation on the document warnings without wiping extract warnings.
    warnings = list(row.warnings or [])
    if truncated and not any(w.get("code") == "text_truncated" for w in warnings):
        warnings.append(
            {
                "code": "text_truncated",
                "message": "Only the first part of a long resume was sent to the model",
            }
        )
    if draft.low_confidence_paths() and not any(
        w.get("code") == "low_confidence_fields" for w in warnings
    ):
        warnings.append(
            {
                "code": "low_confidence_fields",
                "message": "Some fields have low confidence; review them before confirming",
            }
        )
    row.warnings = warnings
    await ctx.session.flush()
    await ctx.session.refresh(row)
    await audit.record(
        ctx,
        action="document.parsed",
        target_type="document",
        target_id=str(row.id),
        after={
            "profile_id": str(profile_id),
            "prompt_version": PROMPT.key,
            "provider": result.provider,
            "model": result.model,
            "truncated": truncated,
            "low_confidence_count": row.parse_quality["low_confidence_count"],
            "counts": {
                "experiences": len(draft.experiences),
                "projects": len(draft.projects),
                "education": len(draft.education),
                "certifications": len(draft.certifications),
                "languages": len(draft.languages),
                "skills": len(draft.skills),
            },
        },
    )
    return row


def _load_draft(
    row: m.Document, override: dict[str, Any] | ProfileExtract | None
) -> ProfileExtract:
    if override is None and not row.parsed:
        raise AppError("draft_missing", "Parse this document before confirming", 422)
    try:
        raw = (
            override
            if isinstance(override, ProfileExtract)
            else ProfileExtract.model_validate(override if override is not None else row.parsed)
        )
        return post_process_draft(raw)
    except ValidationError as exc:
        raise AppError(
            "draft_invalid",
            "Draft is invalid",
            422,
            exc.errors(include_url=False, include_context=False, include_input=False),
        ) from None


async def confirm_document(
    ctx: WorkspaceContext,
    profile_id: uuid.UUID,
    document_id: uuid.UUID,
    body: s.DocumentConfirm,
) -> dict[str, Any]:
    profile = await _get_profile(ctx, profile_id)
    row = await _get_document(ctx, profile_id, document_id)
    quality = dict(row.parse_quality or {})
    if quality.get("confirmed_at"):
        raise AppError("document_already_confirmed", "This document was already confirmed", 409)
    if row.status != "ready":
        raise AppError("document_not_ready", "Document is not ready", 422)
    if await profile_has_facts(ctx, profile_id):
        raise AppError(
            "merge_required",
            "This profile already has facts; preview and resolve a merge instead",
            409,
        )

    draft = _load_draft(row, body.draft)
    created: dict[str, int] = {
        "experiences": 0,
        "projects": 0,
        "bullets": 0,
        "education": 0,
        "certifications": 0,
        "languages": 0,
        "skills": 0,
    }
    header_fields: list[str] = []

    if body.apply_header:
        mapping = {
            "display_name": draft.display_name.value,
            "headline": draft.headline.value,
            "summary": draft.summary.value,
            "location": draft.location.value,
            "timezone": draft.timezone.value,
            "language": draft.language.value,
        }
        for field, value in mapping.items():
            if value is None:
                continue
            if field == "display_name" and not value.strip():
                continue
            if field == "language" and not value.strip():
                continue
            setattr(profile, field, value.strip() if isinstance(value, str) else value)
            header_fields.append(field)
        if draft.links:
            profile.links = [{"label": lk.label, "url": lk.url} for lk in draft.links]
            header_fields.append("links")

    for exp in draft.experiences:
        row_exp = m.Experience(
            workspace_id=ctx.workspace_id,
            profile_id=profile_id,
            company=exp.company,
            title=exp.title,
            employment_type=exp.employment_type,
            location=exp.location,
            start_date=exp.start_date,
            end_date=exp.end_date,
            is_current=exp.is_current,
            description=exp.description,
            source="parsed",
        )
        ctx.session.add(row_exp)
        await ctx.session.flush()
        created["experiences"] += 1
        for b in exp.bullets:
            ctx.session.add(
                m.Bullet(
                    workspace_id=ctx.workspace_id,
                    profile_id=profile_id,
                    experience_id=row_exp.id,
                    text=b.text,
                    metrics=b.metrics,
                    skills=b.skills,
                    evidence_strength=evidence_strength(b.text, b.metrics),
                    source="parsed",
                )
            )
            created["bullets"] += 1

    for proj in draft.projects:
        row_proj = m.Project(
            workspace_id=ctx.workspace_id,
            profile_id=profile_id,
            name=proj.name,
            url=proj.url,
            description=proj.description,
            start_date=proj.start_date,
            end_date=proj.end_date,
            source="parsed",
        )
        ctx.session.add(row_proj)
        await ctx.session.flush()
        created["projects"] += 1
        for b in proj.bullets:
            ctx.session.add(
                m.Bullet(
                    workspace_id=ctx.workspace_id,
                    profile_id=profile_id,
                    project_id=row_proj.id,
                    text=b.text,
                    metrics=b.metrics,
                    skills=b.skills,
                    evidence_strength=evidence_strength(b.text, b.metrics),
                    source="parsed",
                )
            )
            created["bullets"] += 1

    for edu in draft.education:
        ctx.session.add(
            m.Education(
                workspace_id=ctx.workspace_id,
                profile_id=profile_id,
                institution=edu.institution,
                degree=edu.degree,
                field=edu.field,
                start_date=edu.start_date,
                end_date=edu.end_date,
                notes=edu.notes,
                source="parsed",
            )
        )
        created["education"] += 1

    for cert in draft.certifications:
        ctx.session.add(
            m.Certification(
                workspace_id=ctx.workspace_id,
                profile_id=profile_id,
                name=cert.name,
                issuer=cert.issuer,
                kind=cert.kind,
                issued_on=cert.issued_on,
                expires_on=cert.expires_on,
                jurisdiction=cert.jurisdiction,
                source="parsed",
            )
        )
        created["certifications"] += 1

    for lang in draft.languages:
        ctx.session.add(
            m.Language(
                workspace_id=ctx.workspace_id,
                profile_id=profile_id,
                name=lang.name,
                proficiency=lang.proficiency,
                source="parsed",
            )
        )
        created["languages"] += 1

    for skill in draft.skills:
        ctx.session.add(
            m.Skill(
                workspace_id=ctx.workspace_id,
                profile_id=profile_id,
                name=skill.name,
                level=skill.level,
                years=skill.years,
                last_used=skill.last_used,
                source="parsed",
            )
        )
        created["skills"] += 1

    # Persist the (possibly edited) draft and mark confirmed.
    row.parsed = draft.model_dump(mode="json")
    quality["confirmed_at"] = datetime.now(UTC).isoformat()
    quality["low_confidence_paths"] = draft.low_confidence_paths()
    quality["low_confidence_count"] = len(quality["low_confidence_paths"])
    row.parse_quality = quality
    await ctx.session.flush()

    await audit.record(
        ctx,
        action="document.confirmed",
        target_type="document",
        target_id=str(document_id),
        after={
            "profile_id": str(profile_id),
            "header_fields": header_fields,
            "created": created,
            "source": "parsed",
        },
    )
    if header_fields:
        await audit.record(
            ctx,
            action="profile.updated",
            target_type="profile",
            target_id=str(profile_id),
            after={"fields": header_fields, "from_document": str(document_id)},
        )

    return {
        "document_id": document_id,
        "profile_id": profile_id,
        "header_fields": header_fields,
        "created": created,
    }
