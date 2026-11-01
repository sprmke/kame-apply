"""Voice profile: paste samples → style metrics + banned phrases.

Audit stores counts and field names only, never sample text.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.profiles import models as m
from app.profiles import schemas as s
from app.profiles.banned_phrases import DEFAULT_BANNED_PHRASES
from app.profiles.sanitize import strip_sensitive_numbers
from app.profiles.service import _get_profile
from app.profiles.voice_style import analyze_samples


def _reject_sensitive(text: str) -> None:
    _, kinds = strip_sensitive_numbers(text)
    if kinds:
        raise AppError(
            "sensitive_content",
            "Remove government IDs and card numbers from samples",
            422,
            {"kinds": list(kinds)},
        )


def _sample_dicts(samples: list[dict[str, Any]]) -> list[s.VoiceSampleRead]:
    out: list[s.VoiceSampleRead] = []
    for item in samples:
        out.append(
            s.VoiceSampleRead(
                id=uuid.UUID(str(item["id"])),
                text=str(item.get("text") or ""),
                label=item.get("label"),
                created_at=datetime.fromisoformat(str(item["created_at"])),
            )
        )
    return out


def _to_read(row: m.VoiceProfile) -> s.VoiceRead:
    style_raw = row.style or {}
    return s.VoiceRead(
        id=row.id,
        profile_id=row.profile_id,
        samples=_sample_dicts(list(row.samples or [])),
        style=s.VoiceStyle.model_validate(style_raw) if style_raw else s.VoiceStyle(),
        banned_phrases=list(row.banned_phrases or []),
        ai_use_stance=row.ai_use_stance or "",
        analyzed_at=row.analyzed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def _get_or_create(ctx: WorkspaceContext, profile_id: uuid.UUID) -> m.VoiceProfile:
    await _get_profile(ctx, profile_id)
    q = select(m.VoiceProfile).where(m.VoiceProfile.profile_id == profile_id)
    row = (await ctx.session.execute(q)).scalar_one_or_none()
    if row is not None:
        return row
    row = m.VoiceProfile(
        workspace_id=ctx.workspace_id,
        profile_id=profile_id,
        samples=[],
        style={},
        banned_phrases=list(DEFAULT_BANNED_PHRASES),
        created_by=ctx.user_id,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="voice.created",
        target_type="voice",
        target_id=str(row.id),
        after={
            "profile_id": str(profile_id),
            "banned_count": len(row.banned_phrases),
        },
    )
    return row


async def get_voice(ctx: WorkspaceContext, profile_id: uuid.UUID) -> s.VoiceRead:
    row = await _get_or_create(ctx, profile_id)
    return _to_read(row)


async def put_samples(
    ctx: WorkspaceContext, profile_id: uuid.UUID, body: s.VoiceSamplesPut
) -> s.VoiceRead:
    row = await _get_or_create(ctx, profile_id)
    now = datetime.now(UTC)
    stored: list[dict[str, Any]] = []
    for sample in body.samples:
        _reject_sensitive(sample.text)
        stored.append(
            {
                "id": str(uuid.uuid4()),
                "text": sample.text.strip(),
                "label": sample.label,
                "created_at": now.isoformat(),
            }
        )
    row.samples = stored
    if body.analyze:
        texts = [s["text"] for s in stored]
        row.style = analyze_samples(texts)
        row.analyzed_at = now
    await ctx.session.flush()
    await ctx.session.refresh(row)
    await audit.record(
        ctx,
        action="voice.samples_updated",
        target_type="voice",
        target_id=str(row.id),
        after={
            "profile_id": str(profile_id),
            "sample_count": len(stored),
            "analyzed": body.analyze,
            "word_count": (row.style or {}).get("word_count", 0),
        },
    )
    return _to_read(row)


async def analyze_voice(ctx: WorkspaceContext, profile_id: uuid.UUID) -> s.VoiceRead:
    row = await _get_or_create(ctx, profile_id)
    texts = [str(s.get("text") or "") for s in (row.samples or [])]
    if len([t for t in texts if t.strip()]) < 1:
        raise AppError("samples_required", "Add writing samples before analyzing", 422)
    row.style = analyze_samples(texts)
    row.analyzed_at = datetime.now(UTC)
    await ctx.session.flush()
    await ctx.session.refresh(row)
    await audit.record(
        ctx,
        action="voice.analyzed",
        target_type="voice",
        target_id=str(row.id),
        after={
            "profile_id": str(profile_id),
            "sample_count": (row.style or {}).get("sample_count", 0),
            "word_count": (row.style or {}).get("word_count", 0),
        },
    )
    return _to_read(row)


async def update_voice(
    ctx: WorkspaceContext, profile_id: uuid.UUID, body: s.VoiceUpdate
) -> s.VoiceRead:
    row = await _get_or_create(ctx, profile_id)
    changes = body.model_dump(exclude_unset=True)
    if "banned_phrases" in changes and changes["banned_phrases"] is not None:
        row.banned_phrases = changes["banned_phrases"]
    if "summary" in changes and changes["summary"] is not None:
        style = dict(row.style or {})
        style["summary"] = changes["summary"].strip()
        row.style = style
    await ctx.session.flush()
    await ctx.session.refresh(row)
    await audit.record(
        ctx,
        action="voice.updated",
        target_type="voice",
        target_id=str(row.id),
        after={
            "profile_id": str(profile_id),
            "fields": sorted(changes),
            "banned_count": len(row.banned_phrases or []),
        },
    )
    return _to_read(row)
