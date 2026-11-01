"""Answer bank: reusable eligibility and form answers (PRD F1).

Never stores sensitive-class values (government IDs, cards). Audit rows record key, scope,
approved, and field names only — never answer text.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.profiles import models as m
from app.profiles import schemas as s
from app.profiles.answer_keys import (
    CANONICAL_BY_KEY,
    CANONICAL_KEYS,
    SETUP_COUNTRIES,
)
from app.profiles.sanitize import strip_sensitive_numbers
from app.profiles.service import _get_profile

_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,78}$")
_LINK_KEY_LABELS: dict[str, tuple[str, ...]] = {
    "linkedin_url": ("linkedin",),
    "portfolio_url": ("portfolio", "website", "personal"),
    "github_url": ("github",),
}


def _reject_sensitive(text: str) -> None:
    _, kinds = strip_sensitive_numbers(text)
    if kinds:
        raise AppError(
            "sensitive_content",
            "Remove government IDs and card numbers from answers",
            422,
            {"kinds": list(kinds)},
        )


def _validate_key_country(key: str, country: str | None) -> None:
    if not _KEY_RE.match(key):
        raise AppError("invalid_key", "Answer key must be a lowercase snake_case slug", 422)
    meta = CANONICAL_BY_KEY.get(key)
    if meta is not None:
        if meta.country_scoped and not country:
            raise AppError(
                "country_required",
                f"{key} needs a country code",
                422,
                {"key": key},
            )
        if not meta.country_scoped and country:
            raise AppError(
                "country_not_allowed",
                f"{key} is not country-scoped",
                422,
                {"key": key},
            )


def _validate_scope(scope: str, track_id: uuid.UUID | None) -> None:
    if scope == "global" and track_id is not None:
        raise AppError("invalid_scope", "global answers cannot set track_id", 422)
    if scope == "track" and track_id is None:
        raise AppError("invalid_scope", "track-scoped answers need track_id", 422)


def _meta_payload(row: m.AnswerBank) -> dict[str, Any]:
    return {
        "profile_id": str(row.profile_id),
        "key": row.key,
        "country": row.country,
        "scope": row.scope,
        "track_id": str(row.track_id) if row.track_id else None,
        "approved": row.approved,
    }


async def _get_answer(
    ctx: WorkspaceContext, profile_id: uuid.UUID, answer_id: uuid.UUID
) -> m.AnswerBank:
    await _get_profile(ctx, profile_id)
    row = await ctx.session.get(m.AnswerBank, answer_id)
    if row is None or row.profile_id != profile_id or row.workspace_id != ctx.workspace_id:
        raise AppError("answer_not_found", "Answer not found", 404)
    return row


async def _slot_taken(
    ctx: WorkspaceContext,
    profile_id: uuid.UUID,
    *,
    key: str,
    country: str | None,
    scope: str,
    track_id: uuid.UUID | None,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    q = select(m.AnswerBank.id).where(
        m.AnswerBank.profile_id == profile_id,
        m.AnswerBank.key == key,
        m.AnswerBank.scope == scope,
        m.AnswerBank.country.is_(country) if country is None else m.AnswerBank.country == country,
        m.AnswerBank.track_id.is_(track_id)
        if track_id is None
        else m.AnswerBank.track_id == track_id,
    )
    if exclude_id is not None:
        q = q.where(m.AnswerBank.id != exclude_id)
    return (await ctx.session.execute(q.limit(1))).scalar_one_or_none() is not None


async def list_canonical_keys(
    ctx: WorkspaceContext, profile_id: uuid.UUID
) -> list[s.CanonicalKeyRead]:
    await _get_profile(ctx, profile_id)
    return [
        s.CanonicalKeyRead(
            key=k.key,
            label=k.label,
            group=k.group,
            country_scoped=k.country_scoped,
            default_variants=list(k.default_variants),
            default_answer=k.default_answer,
            json_hint=k.json_hint,
        )
        for k in CANONICAL_KEYS
    ]


async def list_answers(
    ctx: WorkspaceContext,
    profile_id: uuid.UUID,
    *,
    key: str | None = None,
    scope: str | None = None,
    country: str | None = None,
    track_id: uuid.UUID | None = None,
    approved: bool | None = None,
    q: str | None = None,
) -> list[m.AnswerBank]:
    await _get_profile(ctx, profile_id)
    stmt = select(m.AnswerBank).where(m.AnswerBank.profile_id == profile_id)
    if key:
        stmt = stmt.where(m.AnswerBank.key == key)
    if scope:
        stmt = stmt.where(m.AnswerBank.scope == scope)
    if country:
        stmt = stmt.where(m.AnswerBank.country == country.upper())
    if track_id is not None:
        stmt = stmt.where(m.AnswerBank.track_id == track_id)
    if approved is not None:
        stmt = stmt.where(m.AnswerBank.approved.is_(approved))
    if q:
        needle = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                m.AnswerBank.key.ilike(needle),
                func.array_to_string(m.AnswerBank.question_variants, " ").ilike(needle),
            )
        )
    stmt = stmt.order_by(m.AnswerBank.sort_order, m.AnswerBank.key, m.AnswerBank.created_at)
    return list((await ctx.session.execute(stmt)).scalars())


async def get_answer(
    ctx: WorkspaceContext, profile_id: uuid.UUID, answer_id: uuid.UUID
) -> m.AnswerBank:
    return await _get_answer(ctx, profile_id, answer_id)


async def create_answer(
    ctx: WorkspaceContext, profile_id: uuid.UUID, body: s.AnswerCreate
) -> m.AnswerBank:
    await _get_profile(ctx, profile_id)
    _validate_key_country(body.key, body.country)
    _validate_scope(body.scope, body.track_id)
    _reject_sensitive(body.answer)
    if body.answer_json is not None:
        _reject_sensitive(str(body.answer_json))
    if await _slot_taken(
        ctx,
        profile_id,
        key=body.key,
        country=body.country,
        scope=body.scope,
        track_id=body.track_id,
    ):
        raise AppError("answer_exists", "An answer already exists for this key and scope", 409)

    variants = body.question_variants
    if not variants and body.key in CANONICAL_BY_KEY:
        variants = list(CANONICAL_BY_KEY[body.key].default_variants)

    row = m.AnswerBank(
        workspace_id=ctx.workspace_id,
        profile_id=profile_id,
        key=body.key,
        country=body.country,
        question_variants=variants,
        answer=body.answer,
        answer_json=body.answer_json,
        scope=body.scope,
        track_id=body.track_id,
        approved=body.approved,
        sort_order=body.sort_order,
        created_by=ctx.user_id,
    )
    ctx.session.add(row)
    try:
        await ctx.session.flush()
    except IntegrityError as exc:
        raise AppError(
            "answer_exists", "An answer already exists for this key and scope", 409
        ) from exc
    await audit.record(
        ctx,
        action="answer.created",
        target_type="answer",
        target_id=str(row.id),
        after=_meta_payload(row),
    )
    return row


async def update_answer(
    ctx: WorkspaceContext,
    profile_id: uuid.UUID,
    answer_id: uuid.UUID,
    body: s.AnswerUpdate,
) -> m.AnswerBank:
    row = await _get_answer(ctx, profile_id, answer_id)
    changes = body.model_dump(exclude_unset=True)
    if "answer" in changes and changes["answer"] is not None:
        _reject_sensitive(changes["answer"])
    if "answer_json" in changes and changes["answer_json"] is not None:
        _reject_sensitive(str(changes["answer_json"]))

    next_scope = changes.get("scope", row.scope)
    next_track = changes["track_id"] if "track_id" in changes else row.track_id
    next_country = changes["country"] if "country" in changes else row.country
    _validate_scope(next_scope, next_track)
    _validate_key_country(row.key, next_country)

    if await _slot_taken(
        ctx,
        profile_id,
        key=row.key,
        country=next_country,
        scope=next_scope,
        track_id=next_track,
        exclude_id=row.id,
    ):
        raise AppError("answer_exists", "An answer already exists for this key and scope", 409)

    for field, value in changes.items():
        setattr(row, field, value)
    try:
        await ctx.session.flush()
    except IntegrityError as exc:
        raise AppError(
            "answer_exists", "An answer already exists for this key and scope", 409
        ) from exc
    await ctx.session.refresh(row)
    await audit.record(
        ctx,
        action="answer.updated",
        target_type="answer",
        target_id=str(row.id),
        after={**_meta_payload(row), "fields": sorted(changes)},
    )
    return row


async def delete_answer(ctx: WorkspaceContext, profile_id: uuid.UUID, answer_id: uuid.UUID) -> None:
    row = await _get_answer(ctx, profile_id, answer_id)
    meta = _meta_payload(row)
    await ctx.session.delete(row)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="answer.deleted",
        target_type="answer",
        target_id=str(answer_id),
        after=meta,
    )


def _link_url(profile: m.CandidateProfile, key: str) -> str:
    labels = _LINK_KEY_LABELS.get(key, ())
    for item in profile.links or []:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").lower()
        url = str(item.get("url") or "").strip()
        if url and any(token in label for token in labels):
            return url
        if key == "linkedin_url" and "linkedin.com" in url.lower():
            return url
        if key == "github_url" and "github.com" in url.lower():
            return url
    return ""


async def setup_answers(
    ctx: WorkspaceContext, profile_id: uuid.UUID, body: s.AnswerSetup
) -> s.AnswerSetupRead:
    """Seed missing canonical rows. Never overwrites existing answers (acceptance scenario 4)."""
    profile = await _get_profile(ctx, profile_id)
    countries = body.countries or list(SETUP_COUNTRIES)
    created_ids: list[uuid.UUID] = []
    skipped = 0

    for meta in CANONICAL_KEYS:
        if meta.key in _LINK_KEY_LABELS and not body.include_links:
            continue
        targets: list[str | None]
        if meta.country_scoped:
            targets = list(countries)
        else:
            targets = [None]

        for country in targets:
            if await _slot_taken(
                ctx,
                profile_id,
                key=meta.key,
                country=country,
                scope="global",
                track_id=None,
            ):
                skipped += 1
                continue
            answer = meta.default_answer
            if meta.key in _LINK_KEY_LABELS:
                answer = _link_url(profile, meta.key)
            # EEO decline defaults are ready to use. Other defaults stay unapproved for review.
            approved = meta.group == "eeo" and bool(answer)
            row = m.AnswerBank(
                workspace_id=ctx.workspace_id,
                profile_id=profile_id,
                key=meta.key,
                country=country,
                question_variants=list(meta.default_variants),
                answer=answer,
                answer_json=None,
                scope="global",
                track_id=None,
                approved=approved,
                sort_order=0,
                created_by=ctx.user_id,
            )
            ctx.session.add(row)
            await ctx.session.flush()
            created_ids.append(row.id)
            await audit.record(
                ctx,
                action="answer.created",
                target_type="answer",
                target_id=str(row.id),
                after={**_meta_payload(row), "setup": True},
            )

    return s.AnswerSetupRead(created=len(created_ids), skipped=skipped, answer_ids=created_ids)
