"""Extension service: tokens, clip, plan-page, log-applied, policies."""

from __future__ import annotations

import hashlib
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select

from app.answers import draft as drafting
from app.answers.restriction import detect_ai_restriction
from app.applications import tracker as app_tracker
from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.extension import brain
from app.extension import models as m
from app.extension import schemas as s
from app.extension.platforms import ALL_PLATFORMS, RESTRICTED_PLATFORMS, detect_platform
from app.extension.tokens import hash_token, new_extension_token
from app.jobs.models import Job, TrackJob
from app.jobs.normalize import normalize_title
from app.profiles import models as pm
from app.profiles.service import get_profile
from app.tracks import models as track_models

_TOKEN_TTL_DAYS = 90


def _redact(value: str | None, pii_class: str) -> str:
    if not value:
        return ""
    if pii_class == "sensitive":
        return "[redacted]"
    if len(value) <= 4:
        return "***"
    return value[:2] + "***" + value[-1]


async def create_token(
    ctx: WorkspaceContext, body: s.ExtensionTokenCreate
) -> s.ExtensionTokenCreated:
    raw = new_extension_token()
    expires = datetime.now(UTC) + timedelta(days=_TOKEN_TTL_DAYS)
    row = m.ExtensionToken(
        workspace_id=ctx.workspace_id,
        user_id=ctx.user_id,
        token_hash=hash_token(raw),
        label=(body.label or "browser")[:80],
        scopes=list(body.scopes or ["extension"]),
        expires_at=expires,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="extension.token.created",
        target_type="extension_token",
        target_id=str(row.id),
        after={"label": row.label, "scopes": row.scopes},
    )
    return s.ExtensionTokenCreated(
        id=row.id,
        token=raw,
        label=row.label,
        scopes=list(row.scopes or []),
        expires_at=row.expires_at,
    )


async def list_tokens(ctx: WorkspaceContext) -> list[s.ExtensionTokenRead]:
    rows = (
        (
            await ctx.session.execute(
                select(m.ExtensionToken)
                .where(
                    m.ExtensionToken.workspace_id == ctx.workspace_id,
                    m.ExtensionToken.user_id == ctx.user_id,
                    m.ExtensionToken.revoked_at.is_(None),
                )
                .order_by(m.ExtensionToken.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [
        s.ExtensionTokenRead(
            id=r.id,
            label=r.label,
            scopes=list(r.scopes or []),
            created_at=r.created_at,
            last_used_at=r.last_used_at,
            expires_at=r.expires_at,
        )
        for r in rows
    ]


async def revoke_token(ctx: WorkspaceContext, token_id: uuid.UUID) -> None:
    row = await ctx.session.get(m.ExtensionToken, token_id)
    if row is None or row.workspace_id != ctx.workspace_id or row.user_id != ctx.user_id:
        raise AppError("not_found", "Token not found", 404)
    if row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        await audit.record(
            ctx,
            action="extension.token.revoked",
            target_type="extension_token",
            target_id=str(row.id),
        )
    await ctx.session.flush()


async def list_policies(ctx: WorkspaceContext) -> list[s.PlatformPolicyRead]:
    rows = (
        (
            await ctx.session.execute(
                select(m.WorkspacePlatformPolicy).where(
                    m.WorkspacePlatformPolicy.workspace_id == ctx.workspace_id
                )
            )
        )
        .scalars()
        .all()
    )
    by_platform = {r.platform: r for r in rows}
    out: list[s.PlatformPolicyRead] = []
    for platform in sorted(ALL_PLATFORMS):
        row = by_platform.get(platform)
        out.append(
            s.PlatformPolicyRead(
                platform=platform,
                autofill_enabled=bool(row.autofill_enabled) if row else False,
                terms_acknowledged_at=row.terms_acknowledged_at if row else None,
            )
        )
    return out


async def put_policy(ctx: WorkspaceContext, body: s.PlatformPolicyPut) -> s.PlatformPolicyRead:
    if body.platform not in ALL_PLATFORMS:
        raise AppError("validation_error", "Unknown platform", 422)
    row = (
        await ctx.session.execute(
            select(m.WorkspacePlatformPolicy).where(
                m.WorkspacePlatformPolicy.workspace_id == ctx.workspace_id,
                m.WorkspacePlatformPolicy.platform == body.platform,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = m.WorkspacePlatformPolicy(
            workspace_id=ctx.workspace_id,
            platform=body.platform,
        )
        ctx.session.add(row)

    if body.autofill_enabled and body.platform in RESTRICTED_PLATFORMS:
        if not body.acknowledge_terms and row.terms_acknowledged_at is None:
            raise AppError(
                "terms_required",
                "Acknowledge platform terms before enabling autofill",
                422,
            )
        if body.acknowledge_terms:
            row.terms_acknowledged_at = datetime.now(UTC)
            row.acknowledged_by = ctx.user_id

    if (
        body.autofill_enabled
        and body.platform in RESTRICTED_PLATFORMS
        and row.terms_acknowledged_at is None
    ):
        raise AppError("terms_required", "Acknowledge platform terms before enabling autofill", 422)

    row.autofill_enabled = body.autofill_enabled
    row.updated_at = datetime.now(UTC)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="extension.platform_policy.updated",
        target_type="workspace_platform_policy",
        target_id=str(row.id),
        after={
            "platform": row.platform,
            "autofill_enabled": row.autofill_enabled,
        },
    )
    return s.PlatformPolicyRead(
        platform=row.platform,
        autofill_enabled=row.autofill_enabled,
        terms_acknowledged_at=row.terms_acknowledged_at,
    )


async def autofill_allowed(ctx: WorkspaceContext, platform: str) -> bool:
    p = (platform or "generic").lower()
    if p not in RESTRICTED_PLATFORMS:
        return True
    row = (
        await ctx.session.execute(
            select(m.WorkspacePlatformPolicy).where(
                m.WorkspacePlatformPolicy.workspace_id == ctx.workspace_id,
                m.WorkspacePlatformPolicy.platform == p,
            )
        )
    ).scalar_one_or_none()
    return bool(row and row.autofill_enabled and row.terms_acknowledged_at)


def _sanitize_clip_text(text: str, limit: int = 8000) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    return t[:limit]


async def clip_job(ctx: WorkspaceContext, body: s.ClipBody) -> s.ClipResult:
    url = (body.url or "").strip()
    if not url or not urlparse(url).scheme.startswith("http"):
        raise AppError("validation_error", "A valid http(s) URL is required", 422)

    title = (body.title or "").strip() or "Untitled job"
    company = (body.company or "").strip()
    if body.json_ld:
        title = str(body.json_ld.get("title") or title)
        org = body.json_ld.get("hiringOrganization") or {}
        if isinstance(org, dict):
            company = str(org.get("name") or company)
        elif isinstance(org, str):
            company = org or company

    platform = (body.platform or detect_platform(url)).lower()
    desc = _sanitize_clip_text(body.description_text)
    # Prefer existing job by canonical URL
    existing = (
        await ctx.session.execute(select(Job).where(Job.canonical_url == url).limit(1))
    ).scalar_one_or_none()
    created = False
    if existing:
        job = existing
        note = "Matched existing job by URL"
    else:
        content_hash = hashlib.sha256(f"clip|{url}|{title}".encode()).hexdigest()
        job = Job(
            title=title[:500],
            normalized_title=normalize_title(title),
            description_text=desc or f"{title} at {company}".strip(),
            description_html="",
            content_hash=content_hash,
            simhash=0,
            canonical_url=url[:1000],
            apply_url=url[:1000],
            status="open",
            meta={
                "company_name": company,
                "clipped": True,
                "platform": platform,
                "source": "extension",
            },
        )
        ctx.session.add(job)
        await ctx.session.flush()
        created = True
        note = "Saved minimal clip; resolve on the employer ATS when possible"

    track_job_id: uuid.UUID | None = None
    track_id = body.track_id
    if track_id is None:
        # Default to first active track
        track = (
            await ctx.session.execute(
                select(track_models.Track)
                .where(
                    track_models.Track.workspace_id == ctx.workspace_id,
                    track_models.Track.archived_at.is_(None),
                    track_models.Track.status == "active",
                )
                .order_by(track_models.Track.sort_order.asc(), track_models.Track.created_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        track_id = track.id if track else None

    if track_id:
        track = await ctx.session.get(track_models.Track, track_id)
        if track is None or track.workspace_id != ctx.workspace_id:
            raise AppError("not_found", "Track not found", 404)
        tj = (
            await ctx.session.execute(
                select(TrackJob).where(
                    TrackJob.workspace_id == ctx.workspace_id,
                    TrackJob.track_id == track_id,
                    TrackJob.job_id == job.id,
                )
            )
        ).scalar_one_or_none()
        if tj is None:
            tj = TrackJob(
                workspace_id=ctx.workspace_id,
                track_id=track_id,
                job_id=job.id,
                status="new",
                eligibility="unknown",
                reasons=[{"kind": "clip", "platform": platform}],
            )
            ctx.session.add(tj)
            await ctx.session.flush()
        track_job_id = tj.id

    await audit.record(
        ctx,
        action="extension.job.clipped",
        target_type="job",
        target_id=str(job.id),
        after={
            "created": created,
            "track_id": str(track_id) if track_id else None,
            "platform": platform,
        },
    )
    risk = None
    if job.meta and isinstance(job.meta, dict):
        risk = job.meta.get("risk_level")
    return s.ClipResult(
        job_id=job.id,
        track_job_id=track_job_id,
        created=created,
        title=job.title,
        company_name=company or (job.meta or {}).get("company_name"),
        risk_level=str(risk) if risk else None,
        note=note,
    )


async def _load_answers(
    ctx: WorkspaceContext, profile_id: uuid.UUID, track_id: uuid.UUID | None
) -> dict[str, str]:
    rows = (
        (
            await ctx.session.execute(
                select(pm.AnswerBank).where(
                    pm.AnswerBank.profile_id == profile_id,
                    pm.AnswerBank.workspace_id == ctx.workspace_id,
                    pm.AnswerBank.approved.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    out: dict[str, str] = {}
    # Prefer track-scoped over global
    for scope in ("global", "track"):
        for row in rows:
            if row.scope != scope:
                continue
            if scope == "track" and track_id and row.track_id != track_id:
                continue
            if scope == "track" and not track_id:
                continue
            text = (row.answer or "").strip()
            if not text and isinstance(row.answer_json, dict):
                text = str(row.answer_json.get("value") or row.answer_json.get("status") or "")
            if text:
                out[row.key] = text
    return out


async def _profile_bundle(ctx: WorkspaceContext, profile_id: uuid.UUID) -> dict[str, Any]:
    profile = await get_profile(ctx, profile_id)
    from app.auth.models import User

    user = await ctx.session.get(User, ctx.user_id)
    return {
        "id": str(profile.id),
        "display_name": profile.display_name,
        "headline": profile.headline,
        "summary": profile.summary,
        "location": profile.location,
        "links": list(profile.links or []),
        "email": user.email if user else None,
        "experiences": [],
        "skills": [],
    }


async def start_run(ctx: WorkspaceContext, body: s.StartRunBody) -> s.StartRunResult:
    await get_profile(ctx, body.profile_id)
    platform = (body.platform or detect_platform(body.page_url) or "generic").lower()
    allowed = await autofill_allowed(ctx, platform)
    run = m.ApplyRun(
        workspace_id=ctx.workspace_id,
        application_id=body.application_id,
        job_id=body.job_id,
        track_id=body.track_id,
        profile_id=body.profile_id,
        source="extension",
        platform=platform,
        page_url=(body.page_url or "")[:2000],
        status="running",
        created_by=ctx.user_id,
    )
    ctx.session.add(run)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="extension.apply_run.started",
        target_type="apply_run",
        target_id=str(run.id),
        after={"platform": platform, "autofill_allowed": allowed},
    )
    return s.StartRunResult(run_id=run.id, status=run.status, autofill_allowed=allowed)


async def plan_page(ctx: WorkspaceContext, body: s.PlanPageBody) -> s.PlanPageResult:
    await get_profile(ctx, body.profile_id)
    platform = (body.platform or detect_platform(body.page_url) or "generic").lower()
    allowed = await autofill_allowed(ctx, platform)

    run: m.ApplyRun | None = None
    if body.run_id:
        run = await ctx.session.get(m.ApplyRun, body.run_id)
        if run is None or run.workspace_id != ctx.workspace_id:
            raise AppError("not_found", "Apply run not found", 404)
    else:
        started = await start_run(
            ctx,
            s.StartRunBody(
                profile_id=body.profile_id,
                platform=platform,
                page_url=body.page_url,
                job_id=body.job_id,
                application_id=body.application_id,
                track_id=body.track_id,
            ),
        )
        run = await ctx.session.get(m.ApplyRun, started.run_id)
        assert run is not None

    answers = await _load_answers(ctx, body.profile_id, body.track_id)
    profile = await _profile_bundle(ctx, body.profile_id)

    sig = brain.signature_hash(ats=platform, fields=body.fields)
    cached_row = (
        await ctx.session.execute(
            select(m.FormSignature).where(m.FormSignature.signature_hash == sig)
        )
    ).scalar_one_or_none()
    cached_map: dict[str, str] = {}
    if cached_row and isinstance(cached_row.field_map, dict):
        cached_map = {str(k): str(v) for k, v in cached_row.field_map.items()}

    instructions, page_restricted, notes = brain.plan_fields(
        fields=body.fields,
        profile=profile,
        answers=answers,
        page_text=body.page_text,
        cached_map=cached_map,
        autofill_allowed=allowed,
    )

    # Persist learned label→canonical mappings (never values)
    new_map = dict(cached_map)
    for field, instr in zip(body.fields, instructions, strict=False):
        if instr.canonical_key:
            label_key = (field.label or field.name or field.id).strip().lower()
            if label_key:
                new_map[field.id] = instr.canonical_key
    if new_map:
        if cached_row is None:
            cached_row = m.FormSignature(signature_hash=sig, ats=platform, field_map=new_map)
            ctx.session.add(cached_row)
        else:
            cached_row.field_map = new_map
            cached_row.updated_at = datetime.now(UTC)

    # Step log (redacted)
    seq_base = (
        await ctx.session.execute(
            select(m.ApplyRunStep.seq)
            .where(m.ApplyRunStep.run_id == run.id)
            .order_by(m.ApplyRunStep.seq.desc())
            .limit(1)
        )
    ).scalar_one_or_none() or 0
    for i, (field, instr) in enumerate(zip(body.fields, instructions, strict=False), start=1):
        ctx.session.add(
            m.ApplyRunStep(
                workspace_id=ctx.workspace_id,
                run_id=run.id,
                seq=seq_base + i,
                page_url=(body.page_url or "")[:2000],
                action=instr.action,
                field_label=(field.label or field.name or field.id)[:200],
                value_redacted=_redact(instr.value, instr.pii_class),
                canonical_key=instr.canonical_key,
                source_fact_ref=instr.source,
                pii_class=instr.pii_class,
            )
        )
    run.updated_at = datetime.now(UTC)
    await ctx.session.flush()

    return s.PlanPageResult(
        run_id=run.id,
        platform=platform,
        autofill_allowed=allowed,
        instructions=instructions,
        page_ai_restricted=page_restricted,
        resume_upload_url=None,
        notes=notes,
    )


async def log_applied(ctx: WorkspaceContext, body: s.LogAppliedBody) -> dict[str, Any]:
    notes = body.notes or ""
    if body.confirmation_url:
        notes = f"{notes}\nConfirmation: {body.confirmation_url}".strip()
    detail = await app_tracker.mark_applied_from_job(
        ctx,
        track_job_id=body.track_job_id,
        job_id=body.job_id,
        track_id=body.track_id,
        method="extension",
        notes=notes,
    )
    if body.run_id:
        run = await ctx.session.get(m.ApplyRun, body.run_id)
        if run and run.workspace_id == ctx.workspace_id:
            run.status = "completed"
            run.application_id = detail.get("id") or run.application_id
            run.updated_at = datetime.now(UTC)
    await audit.record(
        ctx,
        action="extension.application.logged",
        target_type="application",
        target_id=str(detail.get("id")),
        after={"method": "extension"},
    )
    return detail


async def answer_insert(ctx: WorkspaceContext, body: s.AnswerInsertBody) -> s.AnswerInsertResult:
    await get_profile(ctx, body.profile_id)
    hit = detect_ai_restriction(body.question, page_context=body.page_context)
    if hit.restricted:
        return s.AnswerInsertResult(
            draft="",
            ai_restricted=True,
            source="restricted",
            note="This question restricts AI drafts. Type your own answer.",
        )
    profile = await _profile_bundle(ctx, body.profile_id)
    # Pull a few experiences for drafting
    exps = (
        (
            await ctx.session.execute(
                select(pm.Experience)
                .where(pm.Experience.profile_id == body.profile_id)
                .order_by(pm.Experience.sort_order.asc())
                .limit(6)
            )
        )
        .scalars()
        .all()
    )
    profile["experiences"] = [{"title": e.title, "company": e.company} for e in exps]
    skills = (
        (
            await ctx.session.execute(
                select(pm.Skill).where(pm.Skill.profile_id == body.profile_id).limit(16)
            )
        )
        .scalars()
        .all()
    )
    profile["skills"] = [{"name": sk.name} for sk in skills]
    built = drafting.draft_answer(question=body.question, profile=profile)
    return s.AnswerInsertResult(
        draft=str(built.get("draft") or ""),
        ai_restricted=False,
        source=str(built.get("source") or "draft"),
        note=built.get("message"),
    )


async def workspace_summary(ctx: WorkspaceContext) -> dict[str, Any]:
    tracks = (
        (
            await ctx.session.execute(
                select(track_models.Track)
                .where(track_models.Track.workspace_id == ctx.workspace_id)
                .order_by(track_models.Track.created_at.asc())
                .limit(50)
            )
        )
        .scalars()
        .all()
    )
    profiles = (
        (
            await ctx.session.execute(
                select(pm.CandidateProfile)
                .where(pm.CandidateProfile.workspace_id == ctx.workspace_id)
                .order_by(
                    pm.CandidateProfile.is_default.desc(), pm.CandidateProfile.created_at.asc()
                )
                .limit(20)
            )
        )
        .scalars()
        .all()
    )
    return {
        "workspace_id": str(ctx.workspace_id),
        "role": ctx.role,
        "tracks": [
            {
                "id": str(t.id),
                "name": t.name,
                "profile_id": str(t.profile_id),
            }
            for t in tracks
        ],
        "profiles": [
            {
                "id": str(p.id),
                "display_name": p.display_name,
                "is_default": p.is_default,
            }
            for p in profiles
        ],
    }
