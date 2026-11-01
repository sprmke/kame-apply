"""Matching service: extract → score funnel → triage actions → board queries."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text

from app.audit import service as audit
from app.companies.models import Company
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.jobs.models import Job, JobSource, TrackJob
from app.matching.embed import (
    cosine,
    embed_texts,
    job_embed_text,
    similarity_to_score,
    track_embed_text,
)
from app.matching.extract import content_hash, extract_rule_based
from app.matching.feedback import skip_reason_bucket, update_weights
from app.matching.hard_filters import hard_filter
from app.matching.knockout import predict_knockouts
from app.matching.models import HiddenCompany, JobQualification
from app.matching.relax import suggest_relaxations
from app.matching.rule_score import blend_score, clamp_weights, rule_components
from app.matching.verdicts import verdict_for_qual
from app.profiles import models as profile_models
from app.safety.models import JobRisk
from app.sources.models import Source
from app.tracks import models as track_models
from app.tracks.criteria import criteria_from_dict

LLM_TOP_N_DEFAULT = 15


def _job_dict(job: Job, company_name: str | None = None) -> dict[str, Any]:
    return {
        "id": job.id,
        "company_id": job.company_id,
        "company_name": company_name,
        "title": job.title,
        "normalized_title": job.normalized_title,
        "seniority": job.seniority,
        "work_mode": job.work_mode,
        "locations": job.locations,
        "remote_eligibility": job.remote_eligibility,
        "salary": job.salary,
        "skills": job.skills,
        "description_text": job.description_text,
        "posted_at": job.posted_at,
        "apply_url": job.apply_url,
        "canonical_url": job.canonical_url,
        "few_stated_requirements": job.few_stated_requirements,
    }


async def _profile_context(
    ctx: WorkspaceContext, profile_id: uuid.UUID
) -> tuple[dict[str, Any], dict[str, Any], list[str], float]:
    profile = await ctx.session.get(profile_models.CandidateProfile, profile_id)
    if profile is None or profile.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Profile not found", 404)
    skills = list(
        (
            await ctx.session.execute(
                select(profile_models.Skill).where(profile_models.Skill.profile_id == profile_id)
            )
        ).scalars()
    )
    skill_names = [s.name for s in skills if s.name]
    years = 0.0
    exps = list(
        (
            await ctx.session.execute(
                select(profile_models.Experience).where(
                    profile_models.Experience.profile_id == profile_id
                )
            )
        ).scalars()
    )
    for e in exps:
        if e.start_date and e.end_date:
            years += max(0, (e.end_date - e.start_date).days) / 365.25
        elif e.start_date and e.is_current:
            years += max(0, (datetime.now(UTC).date() - e.start_date).days) / 365.25
    answers_rows = list(
        (
            await ctx.session.execute(
                select(profile_models.AnswerBank).where(
                    profile_models.AnswerBank.profile_id == profile_id
                )
            )
        ).scalars()
    )
    answers = {a.key: a.answer_json or {"text": a.answer} for a in answers_rows}
    degrees = list(
        (
            await ctx.session.execute(
                select(profile_models.Education).where(
                    profile_models.Education.profile_id == profile_id
                )
            )
        ).scalars()
    )
    degree_names = [d.degree or d.field or "" for d in degrees]
    langs = list(
        (
            await ctx.session.execute(
                select(profile_models.Language).where(
                    profile_models.Language.profile_id == profile_id
                )
            )
        ).scalars()
    )
    lang_names = [lang.name for lang in langs if lang.name]
    profile_blob = {
        "work_authorization": profile.work_authorization or {},
        "years_experience": years,
        "degrees": degree_names,
        "languages": lang_names,
        "licenses": [],
        "country": (profile.location or "").split(",")[-1].strip()[:2].upper()
        if profile.location
        else "",
    }
    return profile_blob, answers, skill_names, years


async def ensure_qualifications(ctx: WorkspaceContext, job: Job) -> list[JobQualification]:
    h = content_hash(job.title, job.description_text or "")
    if job.qualifications_hash == h:
        rows = list(
            (
                await ctx.session.execute(
                    select(JobQualification)
                    .where(JobQualification.job_id == job.id)
                    .order_by(JobQualification.sort_order)
                )
            ).scalars()
        )
        if rows:
            return rows

    # Replace
    existing = list(
        (
            await ctx.session.execute(
                select(JobQualification).where(JobQualification.job_id == job.id)
            )
        ).scalars()
    )
    for row in existing:
        await ctx.session.delete(row)
    await ctx.session.flush()

    extracted, few = extract_rule_based(
        title=job.title, description=job.description_text or "", skills=list(job.skills or [])
    )
    out: list[JobQualification] = []
    for i, q in enumerate(extracted):
        row = JobQualification(
            job_id=job.id,
            kind=q.kind,
            text=q.text,
            quote=q.quote,
            normalized=q.normalized,
            sort_order=i,
        )
        ctx.session.add(row)
        out.append(row)
    job.qualifications_hash = h
    job.few_stated_requirements = few
    await ctx.session.flush()
    return out


async def _store_embedding(ctx: WorkspaceContext, job: Job, vec: list[float], model: str) -> None:
    lit = "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
    await ctx.session.execute(
        text("UPDATE jobs SET embedding = CAST(:v AS vector), embedding_model = :m WHERE id = :id"),
        {"v": lit, "m": model, "id": job.id},
    )
    job.embedding_model = model


async def score_track_jobs(
    ctx: WorkspaceContext,
    track_id: uuid.UUID,
    *,
    llm_top_n: int = LLM_TOP_N_DEFAULT,
    include_not_eligible: bool = True,
) -> dict[str, Any]:
    track = await ctx.session.get(track_models.Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track not found", 404)
    crit_row = (
        await ctx.session.execute(
            select(track_models.TrackCriteria).where(
                track_models.TrackCriteria.track_id == track_id
            )
        )
    ).scalar_one_or_none()
    structured = (crit_row.structured if crit_row else {}) or {}
    criteria = criteria_from_dict(structured)
    settings = dict(track.settings or {})
    weights = clamp_weights(settings.get("ranking_weights") or {})

    profile_blob, answers, skill_names, years = await _profile_context(ctx, track.profile_id)
    hidden = {
        str(r.company_id)
        for r in (
            await ctx.session.execute(
                select(HiddenCompany).where(
                    HiddenCompany.workspace_id == ctx.workspace_id,
                    (HiddenCompany.track_id.is_(None)) | (HiddenCompany.track_id == track_id),
                )
            )
        ).scalars()
    }

    tjs = list(
        (await ctx.session.execute(select(TrackJob).where(TrackJob.track_id == track_id))).scalars()
    )
    if not tjs:
        return {"scored": 0, "eligible": 0}

    jobs_by_id: dict[uuid.UUID, Job] = {}
    for tj in tjs:
        job = await ctx.session.get(Job, tj.job_id)
        if job and job.status == "open":
            jobs_by_id[job.id] = job

    # Track vector once
    titles = [t.title for t in criteria.titles if not t.exclude]
    track_text = track_embed_text(
        titles=titles or [track.name],
        skills=list(criteria.skills.must) + list(criteria.skills.nice) + skill_names,
    )
    [track_vec], _ = embed_texts([track_text])

    scored = 0
    eligible_n = 0
    scored_rows: list[tuple[TrackJob, float]] = []

    for tj in tjs:
        job = jobs_by_id.get(tj.job_id)
        if job is None:
            continue
        company_name = None
        if job.company_id:
            c = await ctx.session.get(Company, job.company_id)
            company_name = c.name if c else None
        quals = await ensure_qualifications(ctx, job)
        qual_dicts = [
            {
                "id": str(q.id),
                "kind": q.kind,
                "text": q.text,
                "quote": q.quote,
                "normalized": q.normalized,
            }
            for q in quals
        ]
        ko_hits = predict_knockouts(qual_dicts, profile=profile_blob, answers=answers)
        jdict = _job_dict(job, company_name)
        eligibility, detail = hard_filter(
            jdict, criteria, knockout_hits=ko_hits, hidden_company_ids=hidden
        )
        tj.eligibility = eligibility
        tj.eligibility_detail = detail

        comps, reasons = rule_components(
            jdict, criteria, profile_skills=skill_names, profile_seniority=None
        )
        # Semantic
        qtexts = [q.text for q in quals]
        emb_text = job_embed_text(
            title=job.title, summary=job.description_text or "", qualifications=qtexts
        )
        [job_vec], model = embed_texts([emb_text])
        await _store_embedding(ctx, job, job_vec, model)
        sem = similarity_to_score(cosine(track_vec, job_vec))
        comps["semantic"] = sem

        # Verdicts into fit
        profile_skills = {s.lower() for s in skill_names}
        ko_ids = {h.get("qual_id") for h in ko_hits}
        fit_ledger = []
        for q in qual_dicts:
            v = verdict_for_qual(
                q,
                profile_skills=profile_skills,
                profile_years=years,
                profile_degrees={d.lower() for d in profile_blob.get("degrees") or [] if d},
                profile_languages={x.lower() for x in profile_blob.get("languages") or []},
                knockout_hit=q.get("id") in ko_ids,
            )
            fit_ledger.append({**q, **v})

        score = blend_score(comps, weights, semantic=sem)
        # Feedback: similar to skipped "too junior" → penalize seniority component slightly in score
        skip_bias = settings.get("skip_bias") or {}
        if skip_bias.get("too_junior") and (job.seniority or "").lower() in {
            "intern",
            "junior",
            "mid",
        }:
            score = max(0.0, score - min(15.0, 2.0 * float(skip_bias["too_junior"])))
            reasons = [*list(reasons), "Downranked: similar skips"]

        tj.score = score if eligibility == "eligible" else min(score, 35.0)
        tj.score_components = comps
        tj.reasons = reasons[:3]
        tj.fit = {
            "ledger": fit_ledger,
            "few_stated": bool(job.few_stated_requirements),
            "knockouts": ko_hits,
        }
        tj.last_scored_at = datetime.now(UTC)
        tj.ai_review_paused = True  # LLM stage optional; marked paused when skipped
        scored += 1
        if eligibility == "eligible":
            eligible_n += 1
            scored_rows.append((tj, float(tj.score or 0)))

        # Phase 7: cheap risk layers (no network) during score
        try:
            from app.safety.service import assess_and_store

            await assess_and_store(ctx, job.id, run_network=False, run_llm=False)
        except AppError:
            pass
        except Exception as risk_exc:
            # Scoring must not fail closed on risk; record and continue.
            tj.fit = {**(tj.fit or {}), "risk_error": type(risk_exc).__name__}

    # Stage 4 LLM fit for top N — best-effort; never fail the run
    scored_rows.sort(key=lambda x: x[1], reverse=True)
    top = scored_rows[: max(0, llm_top_n)]
    if top:
        try:
            await _llm_fit_batch(ctx, track, top)
            for tj, _ in top:
                tj.ai_review_paused = False
        except AppError as e:
            if e.code in {"ai_not_configured", "budget_reached", "ai_credential_invalid"}:
                for tj, _ in top:
                    tj.ai_review_paused = True
            else:
                raise

    await ctx.session.flush()
    await audit.record(
        ctx,
        action="matching.score_track",
        target_type="track",
        target_id=str(track_id),
        after={"scored": scored, "eligible": eligible_n},
        actor_type="system",
    )
    return {"scored": scored, "eligible": eligible_n}


async def _llm_fit_batch(
    ctx: WorkspaceContext,
    track: track_models.Track,
    rows: list[tuple[TrackJob, float]],
) -> None:
    """Optional structured fit for top N. Uses cheap tier; skipped if no AI."""
    from pydantic import BaseModel, Field

    from app.ai import service as ai_service
    from app.ai.prompts import get_prompt
    from app.core.config import get_settings

    class FitOut(BaseModel):
        score: float = Field(ge=0, le=100)
        reasons: list[str] = Field(default_factory=list)
        gaps: list[str] = Field(default_factory=list)
        seniority_fit: str = "unknown"
        red_flags: list[str] = Field(default_factory=list)

    from app.safety.sanitize import for_ai_context

    settings = get_settings()
    prompt_def = get_prompt("job_fit")
    for tj, _ in rows:
        job = await ctx.session.get(Job, tj.job_id)
        if job is None:
            continue
        job_ctx = for_ai_context(
            f"{job.title}\n{(job.description_text or '')[:3000]}",
            kind="job_posting",
        )
        prompt = (
            f"Track: {track.name}\n"
            f"{job_ctx.delimited}\n"
            f"Current rule score: {tj.score}\nReasons: {tj.reasons}\n"
        )
        result = await ai_service.run_structured(
            ctx,
            settings,
            tier="bulk",
            feature="job_fit",
            system=prompt_def.system,
            prompt=prompt,
            output_type=FitOut,
        )
        fit = dict(tj.fit or {})
        fit["llm"] = result.output.model_dump()
        tj.fit = fit
        comps = dict(tj.score_components or {})
        weights = clamp_weights((track.settings or {}).get("ranking_weights") or {})
        tj.score = blend_score(
            comps, weights, semantic=comps.get("semantic"), llm=result.output.score
        )
        reasons = list(tj.reasons or [])
        for r in result.output.reasons[:2]:
            if r not in reasons:
                reasons.append(r)
        tj.reasons = reasons[:4]


async def list_board(
    ctx: WorkspaceContext,
    *,
    track_id: uuid.UUID | None = None,
    status: str | None = None,
    include_not_eligible: bool = False,
    sort: str = "score",
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    q = (
        select(TrackJob, Job)
        .join(Job, Job.id == TrackJob.job_id)
        .where(Job.status == "open", TrackJob.workspace_id == ctx.workspace_id)
    )
    if track_id:
        track = await ctx.session.get(track_models.Track, track_id)
        if track is None or track.workspace_id != ctx.workspace_id:
            raise AppError("not_found", "Track not found", 404)
        q = q.where(TrackJob.track_id == track_id)
    if status:
        q = q.where(TrackJob.status == status)
    else:
        q = q.where(TrackJob.status.notin_(("hidden",)))
    if not include_not_eligible:
        q = q.where(TrackJob.eligibility != "not_eligible")
    if sort == "newest":
        q = q.order_by(Job.posted_at.desc().nullslast(), TrackJob.created_at.desc())
    elif sort == "salary":
        q = q.order_by(TrackJob.score.desc().nullslast())
    else:
        q = q.order_by(TrackJob.score.desc().nullslast(), TrackJob.created_at.desc())
    q = q.offset(offset).limit(min(limit, 500))
    rows = (await ctx.session.execute(q)).all()
    out = []
    for tj, job in rows:
        company_name = None
        if job.company_id:
            c = await ctx.session.get(Company, job.company_id)
            company_name = c.name if c else None
        risk = await ctx.session.get(JobRisk, job.id)
        out.append(
            {
                "id": tj.id,
                "track_id": tj.track_id,
                "job_id": tj.job_id,
                "score": tj.score,
                "status": tj.status,
                "eligibility": tj.eligibility,
                "reasons": tj.reasons or [],
                "score_components": tj.score_components or {},
                "ai_review_paused": tj.ai_review_paused,
                "skip_reason": tj.skip_reason,
                "seen_at": tj.seen_at,
                "title": job.title,
                "company_name": company_name,
                "company_id": job.company_id,
                "apply_url": job.apply_url,
                "canonical_url": job.canonical_url,
                "work_mode": job.work_mode,
                "locations": job.locations,
                "salary": job.salary,
                "posted_at": job.posted_at,
                "risk_level": risk.level if risk else None,
            }
        )
    return out


async def get_track_job_detail(ctx: WorkspaceContext, track_job_id: uuid.UUID) -> dict[str, Any]:
    tj = await ctx.session.get(TrackJob, track_job_id)
    if tj is None or tj.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Job not found", 404)
    job = await ctx.session.get(Job, tj.job_id)
    if job is None:
        raise AppError("not_found", "Job not found", 404)
    company = await ctx.session.get(Company, job.company_id) if job.company_id else None
    quals = await ensure_qualifications(ctx, job)
    sources = (
        await ctx.session.execute(
            select(JobSource, Source)
            .join(Source, Source.id == JobSource.source_id)
            .where(JobSource.job_id == job.id)
        )
    ).all()
    other_roles: list[dict[str, Any]] = []
    if job.company_id:
        sibs = (
            await ctx.session.execute(
                select(Job)
                .where(
                    Job.company_id == job.company_id,
                    Job.status == "open",
                    Job.id != job.id,
                )
                .limit(8)
            )
        ).scalars()
        other_roles = [{"id": s.id, "title": s.title, "apply_url": s.apply_url} for s in sibs]

    if tj.seen_at is None:
        tj.seen_at = datetime.now(UTC)
        await ctx.session.flush()

    elig_quote = None
    for h in (tj.eligibility_detail or {}).get("knockouts") or []:
        elig_quote = h.get("quote")
        break

    risk_row = await ctx.session.get(JobRisk, job.id)

    return {
        "id": tj.id,
        "track_id": tj.track_id,
        "job_id": tj.job_id,
        "score": tj.score,
        "status": tj.status,
        "eligibility": tj.eligibility,
        "eligibility_quote": elig_quote,
        "eligibility_detail": tj.eligibility_detail,
        "reasons": tj.reasons or [],
        "score_components": tj.score_components or {},
        "fit": tj.fit or {},
        "ai_review_paused": tj.ai_review_paused,
        "title": job.title,
        "company_name": company.name if company else None,
        "company_id": job.company_id,
        "apply_url": job.apply_url,
        "canonical_url": job.canonical_url,
        "work_mode": job.work_mode,
        "locations": job.locations,
        "salary": job.salary,
        "posted_at": job.posted_at,
        "description_html": job.description_html,
        "description_text": job.description_text,
        "few_stated_requirements": job.few_stated_requirements,
        "qualifications": [
            {
                "id": q.id,
                "kind": q.kind,
                "text": q.text,
                "quote": q.quote,
                "normalized": q.normalized,
                **next(
                    (
                        {
                            "verdict": item.get("verdict"),
                            "evidence_quote": item.get("evidence_quote"),
                        }
                        for item in (tj.fit or {}).get("ledger") or []
                        if item.get("id") == str(q.id)
                    ),
                    {"verdict": "not_evidenced", "evidence_quote": None},
                ),
            }
            for q in quals
        ],
        "sources": [{"key": src.key, "name": src.name, "url": js.url} for js, src in sources],
        "other_roles": other_roles,
        "risk_level": risk_row.level if risk_row else None,
        "risk_reasons": list(risk_row.reasons or []) if risk_row else [],
    }


async def triage(
    ctx: WorkspaceContext,
    track_job_id: uuid.UUID,
    *,
    action: str,
    skip_reason: str | None = None,
) -> TrackJob:
    tj = await ctx.session.get(TrackJob, track_job_id)
    if tj is None or tj.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Job not found", 404)
    track = await ctx.session.get(track_models.Track, tj.track_id)
    if track is None:
        raise AppError("not_found", "Track not found", 404)

    before = {"status": tj.status, "skip_reason": tj.skip_reason}
    if action == "shortlist":
        tj.status = "shortlisted"
        tj.skip_reason = None
    elif action == "skip":
        tj.status = "skipped"
        tj.skip_reason = skip_reason or "other"
    elif action == "hide":
        tj.status = "hidden"
    elif action == "applied":
        tj.status = "applied"
        # Cross-track badge: mark same job applied elsewhere
        others = (
            await ctx.session.execute(
                select(TrackJob).where(
                    TrackJob.workspace_id == ctx.workspace_id,
                    TrackJob.job_id == tj.job_id,
                    TrackJob.id != tj.id,
                )
            )
        ).scalars()
        for o in others:
            if o.status not in ("applied", "hidden"):
                fit = dict(o.fit or {})
                fit["applied_elsewhere"] = True
                o.fit = fit
    elif action == "restore":
        tj.status = "new"
        tj.skip_reason = None
    else:
        raise AppError("invalid_action", "Unknown triage action", 422)

    settings = dict(track.settings or {})
    weights = update_weights(
        settings.get("ranking_weights"),
        action=action
        if action in {"shortlist", "skip"}
        else "skip"
        if action == "hide"
        else "shortlist",
        skip_reason=skip_reason_bucket(skip_reason) if action == "skip" else None,
        components=dict(tj.score_components or {}),
    )
    settings["ranking_weights"] = weights
    if action == "skip":
        bucket = skip_reason_bucket(skip_reason)
        bias = dict(settings.get("skip_bias") or {})
        bias[bucket] = float(bias.get(bucket) or 0) + 1.0
        settings["skip_bias"] = bias
    track.settings = settings
    await ctx.session.flush()
    await audit.record(
        ctx,
        action=f"matching.triage.{action}",
        target_type="track_job",
        target_id=str(tj.id),
        before=before,
        after={"status": tj.status, "skip_reason": tj.skip_reason},
    )
    return tj


async def hide_company(
    ctx: WorkspaceContext,
    *,
    company_id: uuid.UUID,
    track_id: uuid.UUID | None = None,
    reason: str = "",
) -> HiddenCompany:
    company = await ctx.session.get(Company, company_id)
    if company is None:
        raise AppError("not_found", "Company not found", 404)
    row = HiddenCompany(
        workspace_id=ctx.workspace_id,
        company_id=company_id,
        track_id=track_id,
        reason=reason[:500],
    )
    ctx.session.add(row)
    # Hide open track jobs for this company in scope
    q = (
        select(TrackJob, Job)
        .join(Job, Job.id == TrackJob.job_id)
        .where(
            TrackJob.workspace_id == ctx.workspace_id,
            Job.company_id == company_id,
        )
    )
    if track_id:
        q = q.where(TrackJob.track_id == track_id)
    for tj, _job in (await ctx.session.execute(q)).all():
        tj.status = "hidden"
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="matching.hide_company",
        target_type="company",
        target_id=str(company_id),
        after={"track_id": str(track_id) if track_id else None},
    )
    return row


async def relaxation_suggestions(
    ctx: WorkspaceContext, track_id: uuid.UUID
) -> list[dict[str, Any]]:
    track = await ctx.session.get(track_models.Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track not found", 404)
    crit_row = (
        await ctx.session.execute(
            select(track_models.TrackCriteria).where(
                track_models.TrackCriteria.track_id == track_id
            )
        )
    ).scalar_one_or_none()
    structured = (crit_row.structured if crit_row else {}) or {}
    rows = (
        await ctx.session.execute(
            select(TrackJob, Job)
            .join(Job, Job.id == TrackJob.job_id)
            .where(TrackJob.track_id == track_id, Job.status == "open")
            .limit(500)
        )
    ).all()
    jobs = []
    for _tj, job in rows:
        company_name = None
        if job.company_id:
            c = await ctx.session.get(Company, job.company_id)
            company_name = c.name if c else None
        jobs.append(_job_dict(job, company_name))
    return suggest_relaxations(
        criteria=structured, jobs=jobs, hard_filter_fn=lambda j, c: hard_filter(j, c)
    )


async def export_csv(
    ctx: WorkspaceContext,
    *,
    track_id: uuid.UUID | None = None,
    include_not_eligible: bool = False,
) -> str:
    rows = await list_board(
        ctx,
        track_id=track_id,
        include_not_eligible=include_not_eligible,
        limit=500,
    )
    buf = io.StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=[
            "score",
            "title",
            "company_name",
            "eligibility",
            "status",
            "work_mode",
            "salary",
            "posted_at",
            "apply_url",
            "reasons",
        ],
    )
    w.writeheader()
    for r in rows:
        sal = r.get("salary") or {}
        w.writerow(
            {
                "score": r.get("score"),
                "title": r.get("title"),
                "company_name": r.get("company_name"),
                "eligibility": r.get("eligibility"),
                "status": r.get("status"),
                "work_mode": r.get("work_mode"),
                "salary": sal.get("min") or sal.get("text") or "",
                "posted_at": r.get("posted_at"),
                "apply_url": r.get("apply_url"),
                "reasons": "; ".join(r.get("reasons") or []),
            }
        )
    return buf.getvalue()
