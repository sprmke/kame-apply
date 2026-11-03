"""Tailor runs and application creation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.applications.models import Application, CoverLetter, TailorRun
from app.audit import service as audit
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.jobs.models import Job, TrackJob
from app.matching import service as matching
from app.profiles import models as pm
from app.resumes.content import ResumeContent
from app.resumes.cover_letter import draft_cover_letter
from app.resumes.cover_letter_ai import draft_cover_letter_ai
from app.resumes.from_profile import build_from_profile
from app.resumes.lens import run_lens
from app.resumes.models import ResumeChange, ResumeVersion
from app.resumes.parse_gate import run_parse_gate
from app.resumes.render import render_all
from app.resumes.review_ai import review_tailored_draft
from app.resumes.service import load_profile_facts, render_version
from app.resumes.tailor import apply_tailor_ops, tailor_once
from app.tracks import models as track_models


def _run_read(
    row: TailorRun, *, cover: CoverLetter | None = None, draft: ResumeVersion | None = None
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": row.id,
        "track_job_id": row.track_job_id,
        "job_id": row.job_id,
        "track_id": row.track_id,
        "profile_id": row.profile_id,
        "status": row.status,
        "base_version_id": row.base_version_id,
        "draft_version_id": row.draft_version_id,
        "cover_letter_id": row.cover_letter_id,
        "lens_before": row.lens_before or {},
        "lens_after": row.lens_after or {},
        "gaps": row.gaps or [],
        "knockouts": row.knockouts or [],
        "proposed_changes": row.proposed_changes or [],
        "progress": row.progress or {},
        "error": row.error or "",
        "created_at": row.created_at,
        "cover_letter": None,
        "draft_content": None,
    }
    if cover:
        out["cover_letter"] = {
            "id": cover.id,
            "content": cover.content,
            "word_count": cover.word_count,
            "company_reason": cover.company_reason,
            "status": cover.status,
            "evidence_refs": cover.evidence_refs or [],
        }
    if draft:
        out["draft_content"] = draft.content or {}
    return out


async def start_tailor(
    ctx: WorkspaceContext,
    track_job_id: uuid.UUID,
    *,
    include_cover_letter: bool = True,
    base_version_id: uuid.UUID | None = None,
    run_structured=None,
    model_factory=None,
) -> dict[str, Any]:
    tj = await ctx.session.get(TrackJob, track_job_id)
    if tj is None or tj.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track job not found", 404)
    track = await ctx.session.get(track_models.Track, tj.track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track not found", 404)
    job = await ctx.session.get(Job, tj.job_id)
    if job is None:
        raise AppError("not_found", "Job not found", 404)

    profile_id = track.profile_id
    run = TailorRun(
        workspace_id=ctx.workspace_id,
        track_job_id=tj.id,
        job_id=job.id,
        track_id=track.id,
        profile_id=profile_id,
        status="running",
        progress={"step": "load"},
    )
    ctx.session.add(run)
    await ctx.session.flush()

    try:
        facts = await load_profile_facts(ctx, profile_id)
        quals_rows = await matching.ensure_qualifications(ctx, job)
        qualifications = [
            {
                "id": str(q.id),
                "kind": q.kind,
                "text": q.text,
                "quote": q.quote,
                "normalized": q.normalized or {},
            }
            for q in quals_rows
        ]

        # Base resume: explicit version, latest track base, or build from profile
        base_row: ResumeVersion | None = None
        if base_version_id:
            base_row = await ctx.session.get(ResumeVersion, base_version_id)
            if base_row is None or base_row.workspace_id != ctx.workspace_id:
                raise AppError("not_found", "Resume not found", 404)
        else:
            base_row = (
                await ctx.session.execute(
                    select(ResumeVersion)
                    .where(
                        ResumeVersion.workspace_id == ctx.workspace_id,
                        ResumeVersion.track_id == track.id,
                        ResumeVersion.kind.in_(("base", "tailored")),
                    )
                    .order_by(ResumeVersion.updated_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()

        if base_row:
            content = ResumeContent.model_validate(base_row.content or {})
            run.base_version_id = base_row.id
        else:
            content = build_from_profile(facts, target_role=job.title or track.name)
            run.progress = {**(run.progress or {}), "step": "built_from_profile"}

        run.progress = {**(run.progress or {}), "step": "lens_before"}
        result = tailor_once(content, qualifications=qualifications, facts=facts)
        result["review"] = await review_tailored_draft(
            ctx,
            get_settings(),
            content=result["content"],
            qualifications=qualifications,
            deterministic_notes=result["review"],
            run_structured=run_structured,
            model_factory=model_factory,
        )
        run.lens_before = result["lens_before"]
        run.lens_after = result["lens_after"]
        run.gaps = result["gaps"]
        run.knockouts = result["knockouts"]
        run.progress = {
            "step": "done",
            "review": result["review"],
            "grade_before": result["lens_before"].get("grade"),
            "grade_after": result["lens_after"].get("grade"),
        }

        draft = ResumeVersion(
            workspace_id=ctx.workspace_id,
            profile_id=profile_id,
            track_id=track.id,
            kind="draft",
            label=f"Tailor: {job.title}"[:200],
            content=result["content"].model_dump(mode="json"),
            parent_id=run.base_version_id,
            lens_report={
                "before": result["lens_before"],
                "after": result["lens_after"],
                "simulation": True,
            },
            template=(base_row.template if base_row else "classic"),
            page_size=(base_row.page_size if base_row else "letter"),
        )
        ctx.session.add(draft)
        await ctx.session.flush()
        run.draft_version_id = draft.id

        # Per-change review: every proposal becomes a row the user can keep or remove.
        applied_ids = {id(p) for p in (result["applied"] or [])}
        proposed_changes: list[dict[str, Any]] = []
        for proposal in result["proposals"]:
            refs: list[uuid.UUID] = []
            for r in proposal.get("evidence_refs") or []:
                try:
                    refs.append(uuid.UUID(str(r)))
                except ValueError:
                    continue
            change = ResumeChange(
                workspace_id=ctx.workspace_id,
                resume_version_id=draft.id,
                path=str(proposal.get("path") or ""),
                op=str(proposal.get("op") or "rewrite"),
                before=str(proposal.get("before") or ""),
                after=str(proposal.get("after") or ""),
                reason=str(proposal.get("reason") or ""),
                evidence_refs=refs,
                status="accepted" if id(proposal) in applied_ids else "rejected",
            )
            ctx.session.add(change)
            await ctx.session.flush()
            proposed_changes.append(
                {**proposal, "change_id": str(change.id), "status": change.status}
            )
        run.proposed_changes = proposed_changes

        # Render + parse gate on draft
        rendered = render_all(result["content"], template=draft.template, page_size=draft.page_size)
        gate = run_parse_gate(
            result["content"], pdf=rendered.pdf, docx=rendered.docx, text=rendered.text
        )
        draft.parse_gate = gate
        if not gate.get("ok"):
            run.error = "parse_gate_failed"
            # Still return ready so user can see; accept will re-render

        cover_row = None
        if include_cover_letter:
            voice = await _load_voice(ctx, profile_id)
            company_name = None
            if job.company_id:
                from app.companies.models import Company

                co = await ctx.session.get(Company, job.company_id)
                company_name = co.name if co else None
            matches = []
            for row in (result["lens_after"].get("qualifications") or [])[:5]:
                if row.get("verdict") == "met" and row.get("evidence_quote"):
                    matches.append(
                        {
                            "text": row.get("text"),
                            "evidence_quote": row.get("evidence_quote"),
                            "evidence_ref": None,
                        }
                    )
            # Prefer bullet evidence refs
            for b in facts.get("bullets") or []:
                if isinstance(b, dict) and b.get("text") and len(matches) < 3:
                    matches.append(
                        {
                            "text": b["text"],
                            "evidence_quote": b["text"],
                            "evidence_ref": b.get("id"),
                        }
                    )
            job_payload = {
                "title": job.title,
                "company_name": company_name or "",
                "description_text": job.description_text or "",
            }
            letter = await draft_cover_letter_ai(
                ctx,
                get_settings(),
                facts=facts,
                job=job_payload,
                matches=matches,
                voice=voice,
                run_structured=run_structured,
                model_factory=model_factory,
            )
            if letter is None:
                letter = draft_cover_letter(
                    facts=facts,
                    job=job_payload,
                    matches=matches,
                    voice=voice,
                )
            refs = []
            for r in letter.get("evidence_refs") or []:
                try:
                    refs.append(uuid.UUID(str(r)))
                except ValueError:
                    continue
            cover_row = CoverLetter(
                workspace_id=ctx.workspace_id,
                profile_id=profile_id,
                job_id=job.id,
                track_id=track.id,
                resume_version_id=draft.id,
                content=letter["content"],
                word_count=letter["word_count"],
                evidence_refs=refs,
                company_reason=letter["company_reason"],
                status="draft",
            )
            ctx.session.add(cover_row)
            await ctx.session.flush()
            run.cover_letter_id = cover_row.id

        # Job closed while tailoring
        if job.status and job.status != "open":
            run.progress = {**(run.progress or {}), "job_closed": True}

        run.status = "ready"
        await audit.record(
            ctx,
            action="tailor.completed",
            target_type="tailor_run",
            target_id=str(run.id),
            after={
                "grade_before": run.progress.get("grade_before"),
                "grade_after": run.progress.get("grade_after"),
                "gaps": len(run.gaps or []),
            },
        )
        await ctx.session.flush()
        return _run_read(run, cover=cover_row, draft=draft)
    except AppError:
        run.status = "failed"
        await ctx.session.flush()
        raise
    except Exception as exc:
        run.status = "failed"
        run.error = "tailor_failed"
        await ctx.session.flush()
        raise AppError("tailor_failed", "Tailoring failed", 500) from exc


async def decide_tailor_change(
    ctx: WorkspaceContext,
    run_id: uuid.UUID,
    change_id: uuid.UUID,
    *,
    status: str,
) -> dict[str, Any]:
    """Keep or remove one proposed change, then rebuild the draft from the base resume."""
    run = await ctx.session.get(TailorRun, run_id)
    if run is None or run.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Tailor run not found", 404)
    if run.status not in {"ready", "accepted"}:
        raise AppError("bad_request", "Tailor run is not ready", 422)
    change = await ctx.session.get(ResumeChange, change_id)
    if (
        change is None
        or change.workspace_id != ctx.workspace_id
        or change.resume_version_id != run.draft_version_id
    ):
        raise AppError("not_found", "Change not found", 404)
    change.status = status
    change.updated_at = datetime.now(UTC)
    await _recompute_tailor_draft(ctx, run)
    await audit.record(
        ctx,
        action="tailor.change_decided",
        target_type="tailor_run",
        target_id=str(run.id),
        after={"change_id": str(change_id), "status": status},
    )
    await ctx.session.flush()
    return await get_tailor_run(ctx, run_id)


async def _recompute_tailor_draft(ctx: WorkspaceContext, run: TailorRun) -> None:
    """Rebuild the draft from the base resume plus the changes the user kept."""
    if not run.draft_version_id:
        raise AppError("bad_request", "No draft resume", 422)
    draft = await ctx.session.get(ResumeVersion, run.draft_version_id)
    if draft is None or draft.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Draft resume not found", 404)

    job = await ctx.session.get(Job, run.job_id)
    if job is None:
        raise AppError("not_found", "Job not found", 404)
    track = await ctx.session.get(track_models.Track, run.track_id)
    facts = await load_profile_facts(ctx, run.profile_id)

    base: ResumeVersion | None = None
    if run.base_version_id:
        base = await ctx.session.get(ResumeVersion, run.base_version_id)
    if base is not None and base.workspace_id == ctx.workspace_id:
        base_content = ResumeContent.model_validate(base.content or {})
    else:
        target = job.title or (track.name if track else None)
        base_content = build_from_profile(facts, target_role=target)

    changes = list(
        (
            await ctx.session.execute(
                select(ResumeChange)
                .where(
                    ResumeChange.resume_version_id == draft.id,
                    ResumeChange.workspace_id == ctx.workspace_id,
                )
                .order_by(ResumeChange.created_at.asc())
            )
        ).scalars()
    )
    proposals = [
        {
            "op": c.op,
            "path": c.path,
            "before": c.before,
            "after": c.after,
            "reason": c.reason,
            "evidence_refs": [str(r) for r in (c.evidence_refs or [])],
        }
        for c in changes
        if c.status == "accepted"
    ]

    quals_rows = await matching.ensure_qualifications(ctx, job)
    qualifications = [
        {
            "id": str(q.id),
            "kind": q.kind,
            "text": q.text,
            "quote": q.quote,
            "normalized": q.normalized or {},
        }
        for q in quals_rows
    ]
    terms = [
        str((q.get("normalized") or {}).get("name") or q.get("quote") or "")
        for q in qualifications
        if q.get("kind") == "must"
    ]
    content, _applied = apply_tailor_ops(
        base_content,
        proposals,
        facts=facts,
        posting_terms=[t for t in terms if t],
    )
    lens_after = run_lens(content, qualifications=qualifications, facts=facts)

    draft.content = content.model_dump(mode="json")
    draft.lens_report = {
        "before": run.lens_before or {},
        "after": lens_after,
        "simulation": True,
    }
    draft.updated_at = datetime.now(UTC)
    run.lens_after = lens_after
    run.proposed_changes = [
        {
            "change_id": str(c.id),
            "op": c.op,
            "path": c.path,
            "before": c.before,
            "after": c.after,
            "reason": c.reason,
            "evidence_refs": [str(r) for r in (c.evidence_refs or [])],
            "status": c.status,
        }
        for c in changes
    ]
    run.updated_at = datetime.now(UTC)


async def get_tailor_run(ctx: WorkspaceContext, run_id: uuid.UUID) -> dict[str, Any]:
    row = await ctx.session.get(TailorRun, run_id)
    if row is None or row.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Tailor run not found", 404)
    cover = None
    draft = None
    if row.cover_letter_id:
        cover = await ctx.session.get(CoverLetter, row.cover_letter_id)
    if row.draft_version_id:
        draft = await ctx.session.get(ResumeVersion, row.draft_version_id)
    return _run_read(row, cover=cover, draft=draft)


async def accept_tailor(
    ctx: WorkspaceContext,
    run_id: uuid.UUID,
    *,
    include_cover_letter: bool = True,
    method: str = "manual",
) -> dict[str, Any]:
    row = await ctx.session.get(TailorRun, run_id)
    if row is None or row.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Tailor run not found", 404)
    if row.status not in {"ready", "accepted"}:
        raise AppError("bad_request", "Tailor run is not ready", 422)
    if not row.draft_version_id:
        raise AppError("bad_request", "No draft resume", 422)

    draft = await ctx.session.get(ResumeVersion, row.draft_version_id)
    if draft is None or draft.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Draft resume not found", 404)

    # Re-render + parse gate
    render_out = await render_version(ctx, draft.id)
    if not (render_out.get("parse_gate") or {}).get("ok"):
        raise AppError("parse_gate_failed", "Export failed the parse check", 422)

    draft.kind = "tailored"
    draft.accepted_at = datetime.now(UTC)
    draft.updated_at = datetime.now(UTC)

    cover_id = row.cover_letter_id if include_cover_letter else None
    if cover_id:
        cover = await ctx.session.get(CoverLetter, cover_id)
        if cover and cover.workspace_id == ctx.workspace_id:
            cover.status = "accepted"

    job = await ctx.session.get(Job, row.job_id)
    status = "ready"
    if job and job.status and job.status != "open":
        status = "job_closed"

    existing = (
        await ctx.session.execute(
            select(Application).where(
                Application.workspace_id == ctx.workspace_id,
                Application.track_id == row.track_id,
                Application.job_id == row.job_id,
            )
        )
    ).scalar_one_or_none()

    company = ((job.meta or {}).get("company_name") or "") if job else ""
    title = job.title if job else ""
    apply_url = (job.apply_url or job.canonical_url or "") if job else ""
    grade = str((row.lens_after or {}).get("grade") or (row.lens_after or {}).get("letter") or "")[
        :8
    ]

    if existing:
        # Re-tailor: keep version history via parent_id; point application at new version
        existing.resume_version_id = draft.id
        existing.cover_letter_id = cover_id
        existing.lens_before = row.lens_before or {}
        existing.lens_after = row.lens_after or {}
        existing.status = status
        existing.method = method
        existing.tailored = True
        existing.lens_grade = grade
        existing.company_name = company or existing.company_name
        existing.job_title = title or existing.job_title
        existing.apply_url = apply_url or existing.apply_url
        existing.updated_at = datetime.now(UTC)
        app = existing
    else:
        app = Application(
            workspace_id=ctx.workspace_id,
            track_id=row.track_id,
            job_id=row.job_id,
            track_job_id=row.track_job_id,
            profile_id=row.profile_id,
            status=status,
            method=method,
            resume_version_id=draft.id,
            cover_letter_id=cover_id,
            lens_before=row.lens_before or {},
            lens_after=row.lens_after or {},
            company_name=company,
            job_title=title,
            apply_url=apply_url,
            tailored=True,
            lens_grade=grade,
        )
        ctx.session.add(app)

    draft.application_id = None  # set after flush if column used loosely
    await ctx.session.flush()
    # Link draft to application id
    draft.application_id = app.id
    row.status = "accepted"
    row.updated_at = datetime.now(UTC)

    # Mark track job shortlisted/ready path
    tj = await ctx.session.get(TrackJob, row.track_job_id)
    if tj and tj.status in {"new", "seen"}:
        tj.status = "shortlisted"

    await audit.record(
        ctx,
        action="application.ready",
        target_type="application",
        target_id=str(app.id),
        after={
            "resume_version_id": str(draft.id),
            "status": status,
            "tailor_run_id": str(row.id),
        },
    )
    await ctx.session.flush()
    from app.applications import tracker as tracker_svc

    return await tracker_svc.get_application_detail(ctx, app.id)


async def list_applications(ctx: WorkspaceContext) -> list[dict[str, Any]]:
    rows = (
        await ctx.session.execute(
            select(Application)
            .where(Application.workspace_id == ctx.workspace_id)
            .order_by(Application.updated_at.desc())
        )
    ).scalars()
    return [
        {
            "id": r.id,
            "track_id": r.track_id,
            "job_id": r.job_id,
            "track_job_id": r.track_job_id,
            "profile_id": r.profile_id,
            "status": r.status,
            "method": r.method,
            "resume_version_id": r.resume_version_id,
            "cover_letter_id": r.cover_letter_id,
            "lens_before": r.lens_before or {},
            "lens_after": r.lens_after or {},
            "notes": r.notes or "",
            "created_at": r.created_at,
            "submitted_at": r.submitted_at,
        }
        for r in rows
    ]


async def get_application(ctx: WorkspaceContext, app_id: uuid.UUID) -> dict[str, Any]:
    rows = await list_applications(ctx)
    for r in rows:
        if r["id"] == app_id:
            return r
    raise AppError("not_found", "Application not found", 404)


async def _load_voice(ctx: WorkspaceContext, profile_id: uuid.UUID) -> dict[str, Any] | None:
    row = (
        await ctx.session.execute(
            select(pm.VoiceProfile).where(
                pm.VoiceProfile.profile_id == profile_id,
                pm.VoiceProfile.workspace_id == ctx.workspace_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        return None
    return {"style": row.style or {}, "banned_phrases": list(row.banned_phrases or [])}
