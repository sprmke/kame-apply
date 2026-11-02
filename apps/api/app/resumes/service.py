"""Resume Studio service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text

from app.audit import service as audit
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.profiles import models as pm
from app.resumes.content import ResumeContent
from app.resumes.critique import critique_resume
from app.resumes.from_profile import build_from_profile
from app.resumes.generate import apply_accepted_changes, propose_improvements
from app.resumes.insights import compute_market_insights
from app.resumes.models import MarketInsight, ResumeChange, ResumeVersion
from app.resumes.parse_gate import run_parse_gate
from app.resumes.render import parse_view, render_all
from app.resumes.verify import verify_content
from app.tracks import models as track_models


async def load_profile_facts(ctx: WorkspaceContext, profile_id: uuid.UUID) -> dict[str, Any]:
    profile = await ctx.session.get(pm.CandidateProfile, profile_id)
    if profile is None or profile.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Profile not found", 404)

    async def _rows(model):
        return list(
            (
                await ctx.session.execute(
                    select(model).where(
                        model.profile_id == profile_id,
                        model.do_not_use.is_(False),
                    )
                )
            ).scalars()
        )

    experiences = await _rows(pm.Experience)
    projects = await _rows(pm.Project)
    bullets = await _rows(pm.Bullet)
    skills = await _rows(pm.Skill)
    education = await _rows(pm.Education)
    certifications = await _rows(pm.Certification)
    contact_email = (
        await ctx.session.execute(
            text("SELECT email FROM users WHERE id = CAST(:u AS uuid)"), {"u": str(ctx.user_id)}
        )
    ).scalar_one_or_none()
    phone = (
        await ctx.session.execute(
            text(
                "SELECT answer FROM answer_bank WHERE profile_id = CAST(:p AS uuid) "
                "AND key = 'phone' AND coalesce(answer, '') <> '' LIMIT 1"
            ),
            {"p": str(profile_id)},
        )
    ).scalar_one_or_none()

    def _d(obj, *fields) -> dict[str, Any]:
        out: dict[str, Any] = {"id": str(obj.id)}
        for f in fields:
            out[f] = getattr(obj, f, None)
        return out

    links = []
    for item in profile.links or []:
        if isinstance(item, dict) and item.get("url"):
            links.append(item["url"])
        elif isinstance(item, str):
            links.append(item)

    return {
        "id": str(profile.id),
        "display_name": profile.display_name,
        "headline": profile.headline,
        "summary": profile.summary,
        "location": profile.location,
        "email": contact_email,
        "phone": phone,
        "work_authorization": profile.work_authorization or {},
        "links": links,
        "experiences": [
            _d(
                e,
                "company",
                "title",
                "location",
                "start_date",
                "end_date",
                "is_current",
                "description",
            )
            for e in experiences
        ],
        "projects": [
            _d(p, "name", "url", "description", "start_date", "end_date") for p in projects
        ],
        "bullets": [
            {
                "id": str(b.id),
                "experience_id": str(b.experience_id) if b.experience_id else None,
                "project_id": str(b.project_id) if b.project_id else None,
                "text": b.text,
                "metrics": b.metrics,
                "skills": b.skills,
            }
            for b in bullets
        ],
        "skills": [
            {
                "id": str(s.id),
                "name": s.name,
                "level": s.level,
                "years": float(s.years) if s.years else None,
            }
            for s in skills
        ],
        "education": [
            _d(e, "institution", "degree", "field", "start_date", "end_date") for e in education
        ],
        "certifications": [_d(c, "name", "issuer", "kind", "issued_on") for c in certifications],
    }


def _version_read(row: ResumeVersion) -> dict[str, Any]:
    return {
        "id": row.id,
        "profile_id": row.profile_id,
        "track_id": row.track_id,
        "kind": row.kind,
        "label": row.label,
        "template": row.template,
        "page_size": row.page_size,
        "content": row.content or {},
        "critique": row.critique or {},
        "parse_gate": row.parse_gate or {},
        "r2_pdf": row.r2_pdf,
        "r2_docx": row.r2_docx,
        "r2_txt": row.r2_txt,
        "accepted_at": row.accepted_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


async def list_versions(
    ctx: WorkspaceContext, *, track_id: uuid.UUID | None = None, profile_id: uuid.UUID | None = None
) -> list[dict[str, Any]]:
    q = select(ResumeVersion).where(ResumeVersion.workspace_id == ctx.workspace_id)
    if track_id:
        q = q.where(ResumeVersion.track_id == track_id)
    if profile_id:
        q = q.where(ResumeVersion.profile_id == profile_id)
    q = q.order_by(ResumeVersion.updated_at.desc())
    rows = (await ctx.session.execute(q)).scalars()
    return [_version_read(r) for r in rows]


async def create_base(
    ctx: WorkspaceContext,
    *,
    profile_id: uuid.UUID,
    track_id: uuid.UUID | None,
    label: str = "",
    template: str = "classic",
    page_size: str = "letter",
) -> dict[str, Any]:
    facts = await load_profile_facts(ctx, profile_id)
    target = None
    if track_id:
        track = await ctx.session.get(track_models.Track, track_id)
        if track is None or track.workspace_id != ctx.workspace_id:
            raise AppError("not_found", "Track not found", 404)
        target = track.name
        if track.profile_id != profile_id:
            raise AppError("bad_request", "Track profile mismatch", 422)
    content = build_from_profile(facts, target_role=target)
    vr = verify_content(content, facts)
    if not vr.ok:
        # Drop lines that fail rather than inventing; keep structure
        bad_ids = {r["line_id"] for r in vr.rejected}
        if content.summary and content.summary.id in bad_ids:
            content.summary = None
        for sec in content.sections:
            sec.lines = [line for line in sec.lines if line.id not in bad_ids]
            for it in sec.items:
                it.lines = [line for line in it.lines if line.id not in bad_ids]

    row = ResumeVersion(
        workspace_id=ctx.workspace_id,
        profile_id=profile_id,
        track_id=track_id,
        kind="base",
        label=label or (target or "Base resume"),
        content=content.model_dump(mode="json"),
        template=template,
        page_size=page_size,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="resume.created",
        target_type="resume_version",
        target_id=str(row.id),
        after={"track_id": str(track_id) if track_id else None},
    )
    return _version_read(row)


async def get_version(ctx: WorkspaceContext, version_id: uuid.UUID) -> ResumeVersion:
    row = await ctx.session.get(ResumeVersion, version_id)
    if row is None or row.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Resume not found", 404)
    return row


async def critique(ctx: WorkspaceContext, version_id: uuid.UUID) -> dict[str, Any]:
    row = await get_version(ctx, version_id)
    content = ResumeContent.model_validate(row.content or {})
    insights = None
    if row.track_id:
        mi = (
            await ctx.session.execute(
                select(MarketInsight).where(
                    MarketInsight.track_id == row.track_id,
                    MarketInsight.window_days == 30,
                )
            )
        ).scalar_one_or_none()
        if mi:
            insights = {"skills": mi.skills, "comparison": mi.comparison}
    report = critique_resume(
        content,
        market_skills=(insights or {}).get("skills"),
        target_role=content.target_role,
    )
    row.critique = report
    row.updated_at = datetime.now(UTC)
    await audit.record(
        ctx,
        action="resume.critiqued",
        target_type="resume_version",
        target_id=str(row.id),
        after={"fixes": len(report.get("top_fixes") or [])},
        actor_type="system",
    )
    await ctx.session.flush()
    return report


async def improve(
    ctx: WorkspaceContext, version_id: uuid.UUID, *, window_days: int = 30
) -> list[dict[str, Any]]:
    row = await get_version(ctx, version_id)
    facts = await load_profile_facts(ctx, row.profile_id)
    content = ResumeContent.model_validate(row.content or {})
    if not row.critique:
        await critique(ctx, version_id)
        await ctx.session.refresh(row)
    insights_payload = None
    if row.track_id:
        insights_payload = await refresh_insights(ctx, row.track_id, window_days=window_days)
    proposals = propose_improvements(
        content, critique=row.critique or {}, insights=insights_payload, facts=facts
    )
    # Clear old proposed
    old = (
        await ctx.session.execute(
            select(ResumeChange).where(
                ResumeChange.resume_version_id == row.id,
                ResumeChange.status == "proposed",
            )
        )
    ).scalars()
    for o in old:
        await ctx.session.delete(o)

    out = []
    for p in proposals:
        refs = []
        for r in p.get("evidence_refs") or []:
            try:
                refs.append(uuid.UUID(str(r)))
            except ValueError:
                continue
        ask = p.get("ask")
        after_text = p.get("after") or ""
        if p.get("op") == "ask_metric" and ask and not after_text:
            after_text = str(ask)
        ch = ResumeChange(
            workspace_id=ctx.workspace_id,
            resume_version_id=row.id,
            path=p.get("path") or "",
            op=p.get("op") or "rewrite",
            before=p.get("before") or "",
            after=after_text,
            reason=p.get("reason") or "",
            evidence_refs=refs,
            status="proposed",
        )
        ctx.session.add(ch)
        await ctx.session.flush()
        out.append(
            {
                "id": ch.id,
                "path": ch.path,
                "op": ch.op,
                "before": ch.before,
                "after": ch.after if ch.op != "ask_metric" else "",
                "reason": ch.reason,
                "evidence_refs": ch.evidence_refs,
                "status": ch.status,
                "ask": ask or (ch.after if ch.op == "ask_metric" else None),
            }
        )
    await audit.record(
        ctx,
        action="resume.improve_proposed",
        target_type="resume_version",
        target_id=str(row.id),
        after={"count": len(out)},
    )
    return out


async def decide_change(ctx: WorkspaceContext, change_id: uuid.UUID, *, status: str) -> None:
    ch = await ctx.session.get(ResumeChange, change_id)
    if ch is None or ch.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Change not found", 404)
    ch.status = status
    ch.updated_at = datetime.now(UTC)
    await audit.record(
        ctx,
        action="resume.change_decided",
        target_type="resume_change",
        target_id=str(ch.id),
        after={"status": status},
    )
    await ctx.session.flush()


async def bulk_decide(
    ctx: WorkspaceContext,
    version_id: uuid.UUID,
    *,
    status: str,
    change_ids: list[uuid.UUID] | None = None,
) -> None:
    await get_version(ctx, version_id)
    q = select(ResumeChange).where(
        ResumeChange.resume_version_id == version_id,
        ResumeChange.workspace_id == ctx.workspace_id,
        ResumeChange.status == "proposed",
    )
    if change_ids:
        q = q.where(ResumeChange.id.in_(change_ids))
    rows = list((await ctx.session.execute(q)).scalars())
    for ch in rows:
        ch.status = status
        ch.updated_at = datetime.now(UTC)
    await audit.record(
        ctx,
        action="resume.changes_bulk",
        target_type="resume_version",
        target_id=str(version_id),
        after={"status": status, "count": len(rows)},
    )
    await ctx.session.flush()


async def apply_decisions(ctx: WorkspaceContext, version_id: uuid.UUID) -> dict[str, Any]:
    row = await get_version(ctx, version_id)
    changes = list(
        (
            await ctx.session.execute(
                select(ResumeChange).where(ResumeChange.resume_version_id == row.id)
            )
        ).scalars()
    )
    content = ResumeContent.model_validate(row.content or {})
    accepted = [
        {
            "op": c.op,
            "path": c.path,
            "before": c.before,
            "after": c.after,
            "evidence_refs": [str(x) for x in (c.evidence_refs or [])],
            "status": c.status,
        }
        for c in changes
        if c.status == "accepted"
    ]
    new_content = apply_accepted_changes(content, accepted)
    facts = await load_profile_facts(ctx, row.profile_id)
    vr = verify_content(new_content, facts)
    if not vr.ok:
        raise AppError(
            "fabrication_detected",
            "Accepted changes failed truthfulness checks",
            422,
        )
    row.content = new_content.model_dump(mode="json")
    row.accepted_at = datetime.now(UTC)
    row.updated_at = datetime.now(UTC)
    await audit.record(
        ctx,
        action="resume.changes_applied",
        target_type="resume_version",
        target_id=str(row.id),
        after={"accepted": len(accepted)},
    )
    await ctx.session.flush()
    return _version_read(row)


async def render_version(
    ctx: WorkspaceContext,
    version_id: uuid.UUID,
    *,
    template: str | None = None,
    page_size: str | None = None,
    broken: bool = False,
) -> dict[str, Any]:
    row = await get_version(ctx, version_id)
    if broken and get_settings().is_prod:
        raise AppError("bad_request", "broken is a development-only flag", 400)
    content = ResumeContent.model_validate(row.content or {})
    tpl = template or row.template
    size = page_size or row.page_size
    result = render_all(content, template=tpl, page_size=size, broken=broken)
    gate = run_parse_gate(content, pdf=result.pdf, docx=result.docx, text=result.text)
    if broken:
        gate["ok"] = False
        gate.setdefault("diagnostics", []).append("deliberately_broken_template")

    pdf_url = docx_url = txt_url = None
    key_base = f"ws/{ctx.workspace_id}/resumes/{row.id}/{result.filename_base}"
    if result.pdf:
        row.r2_pdf = f"{key_base}.pdf"
    row.r2_docx = f"{key_base}.docx"
    row.r2_txt = f"{key_base}.txt"
    row.parse_gate = gate
    row.template = tpl
    row.page_size = size
    row.updated_at = datetime.now(UTC)

    try:
        from app.core.storage import build_storage

        store = build_storage(get_settings())
        await store.ensure_bucket()
        pdf_key = row.r2_pdf
        docx_key = row.r2_docx
        txt_key = row.r2_txt
        if result.pdf and pdf_key:
            await store.put(pdf_key, result.pdf, "application/pdf")
            pdf_url = await store.presign_get(pdf_key)
        if docx_key:
            await store.put(
                docx_key,
                result.docx,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            docx_url = await store.presign_get(docx_key)
        if txt_key:
            await store.put(txt_key, result.text.encode("utf-8"), "text/plain")
            txt_url = await store.presign_get(txt_key)
    except Exception:
        # Never hand the client an object key disguised as a URL.
        raise AppError(
            "storage_unavailable",
            "Rendered files could not be stored. Try again.",
            502,
        ) from None

    await audit.record(
        ctx,
        action="resume.rendered",
        target_type="resume_version",
        target_id=str(row.id),
        after={"parse_ok": gate.get("ok"), "engine": result.engine},
    )
    await ctx.session.flush()
    if not gate.get("ok") and not broken:
        raise AppError("parse_gate_failed", "Render failed the parse round-trip gate", 422)
    return {
        "parse_gate": gate,
        "pdf_url": pdf_url,
        "docx_url": docx_url,
        "txt_url": txt_url,
        "engine": result.engine,
        "filename_base": result.filename_base,
    }


async def refresh_insights(
    ctx: WorkspaceContext, track_id: uuid.UUID, *, window_days: int = 30
) -> dict[str, Any]:
    track = await ctx.session.get(track_models.Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track not found", 404)
    facts = await load_profile_facts(ctx, track.profile_id)
    profile_skills = {str(s["name"]).lower() for s in facts.get("skills") or []}
    # Resume skills: latest base for track if any
    resume_skills: set[str] = set()
    ver = (
        await ctx.session.execute(
            select(ResumeVersion)
            .where(
                ResumeVersion.track_id == track_id,
                ResumeVersion.workspace_id == ctx.workspace_id,
            )
            .order_by(ResumeVersion.updated_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if ver:
        content = ResumeContent.model_validate(ver.content or {})
        for sec in content.sections:
            if sec.kind == "skills":
                resume_skills.update(line.text.lower() for line in sec.lines)

    payload = await compute_market_insights(
        ctx.session,
        track_id=track_id,
        profile_skills=profile_skills,
        resume_skill_names=resume_skills,
        window_days=window_days,
    )
    existing = (
        await ctx.session.execute(
            select(MarketInsight).where(
                MarketInsight.track_id == track_id,
                MarketInsight.window_days == window_days,
            )
        )
    ).scalar_one_or_none()
    if existing:
        for k, v in payload.items():
            if k == "computed_at":
                existing.computed_at = datetime.now(UTC)
            elif hasattr(existing, k):
                setattr(existing, k, v)
        row = existing
    else:
        row = MarketInsight(
            workspace_id=ctx.workspace_id,
            track_id=track_id,
            window_days=window_days,
            sample_size=payload["sample_size"],
            skills=payload["skills"],
            titles=payload["titles"],
            salary=payload["salary"],
            years_required=payload["years_required"],
            certifications=payload["certifications"],
            comparison=payload["comparison"],
            secondary_research=payload.get("secondary_research") or {},
            low_confidence=payload["low_confidence"],
        )
        ctx.session.add(row)
    await audit.record(
        ctx,
        action="resume.insights_computed",
        target_type="track",
        target_id=str(track_id),
        after={"sample_size": payload["sample_size"], "low_confidence": payload["low_confidence"]},
        actor_type="system",
    )
    await ctx.session.flush()
    return {
        "track_id": track_id,
        "window_days": row.window_days,
        "sample_size": row.sample_size,
        "low_confidence": row.low_confidence,
        "skills": row.skills,
        "titles": row.titles,
        "salary": row.salary,
        "years_required": row.years_required,
        "certifications": row.certifications,
        "comparison": row.comparison,
        "computed_at": row.computed_at,
    }


async def get_parse_view(ctx: WorkspaceContext, version_id: uuid.UUID) -> dict[str, Any]:
    row = await get_version(ctx, version_id)
    content = ResumeContent.model_validate(row.content or {})
    return parse_view(content)


async def list_changes(ctx: WorkspaceContext, version_id: uuid.UUID) -> list[dict[str, Any]]:
    await get_version(ctx, version_id)
    rows = (
        await ctx.session.execute(
            select(ResumeChange)
            .where(ResumeChange.resume_version_id == version_id)
            .order_by(ResumeChange.created_at.asc())
        )
    ).scalars()
    return [
        {
            "id": r.id,
            "path": r.path,
            "op": r.op,
            "before": r.before,
            "after": "" if r.op == "ask_metric" else r.after,
            "reason": r.reason,
            "evidence_refs": r.evidence_refs or [],
            "status": r.status,
            "ask": r.after if r.op == "ask_metric" else None,
        }
        for r in rows
    ]
