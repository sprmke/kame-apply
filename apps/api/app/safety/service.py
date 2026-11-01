"""Persist job risk, overrides, Check-this, mid-run signals."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.jobs.models import Job, TrackJob
from app.safety.assess import assess_job_text
from app.safety.check_this import analyze_text, analyze_url
from app.safety.models import JobRisk, RiskOverride
from app.safety.pii import classify_field


async def _community_signal(session, job_id: uuid.UUID) -> tuple[int, list[dict[str, Any]]]:
    """L7: count reported decisions across workspaces (capped). One vote per workspace."""
    # Reports are tenant-scoped; aggregate with a privileged count. App role sees only own
    # workspace under RLS, so we use a raw count of this workspace's report as local signal
    # and store a soft global hint on job_risk.layers when writing. For true cross-workspace
    # aggregation, a future system job with BYPASSRLS migration role can refresh; here we
    # weight the current workspace report lightly and bump via upsert metadata.
    q = await session.execute(
        select(func.count())
        .select_from(RiskOverride)
        .where(RiskOverride.job_id == job_id, RiskOverride.decision == "reported")
    )
    n = int(q.scalar_one() or 0)
    if n <= 0:
        return 0, []
    delta = min(25, 10 + 5 * (n - 1))
    return delta, [
        {
            "signal": "community_report",
            "layer": "L7",
            "weight": delta,
            "evidence": f"{n} workspace report(s)",
        }
    ]


async def assess_and_store(
    ctx: WorkspaceContext,
    job_id: uuid.UUID,
    *,
    run_network: bool = True,
    run_llm: bool = False,
    extra_signals: list[dict[str, Any]] | None = None,
) -> JobRisk:
    job = await ctx.session.get(Job, job_id)
    if job is None:
        raise AppError("not_found", "Job not found", 404)

    company_domain = None
    company_verified = False
    if job.company_id:
        from app.companies.models import Company

        company = await ctx.session.get(Company, job.company_id)
        if company:
            company_domain = company.domain
            meta = company.meta or {}
            company_verified = bool(meta.get("verified_domain") or meta.get("directory_verified"))

    source_kind = None
    # Prefer first job_sources adapter kind if present.
    from app.jobs.models import JobSource
    from app.sources.models import Source

    js = (
        await ctx.session.execute(select(JobSource).where(JobSource.job_id == job_id).limit(1))
    ).scalar_one_or_none()
    if js:
        src = await ctx.session.get(Source, js.source_id)
        if src:
            source_kind = src.kind

    community_delta, community_reasons = await _community_signal(ctx.session, job_id)

    assessment = assess_job_text(
        title=job.title,
        description_html=job.description_html or "",
        description_text=job.description_text or "",
        apply_url=job.apply_url,
        canonical_url=job.canonical_url,
        source_kind=source_kind,
        company_domain=company_domain,
        company_verified=company_verified,
        salary=job.salary or {},
        community_delta=community_delta,
        community_reasons=community_reasons,
        extra_signals=extra_signals,
        run_network=run_network,
        run_llm=run_llm,
    )

    stmt = (
        pg_insert(JobRisk)
        .values(
            job_id=job_id,
            level=assessment.level,
            score=assessment.score,
            reasons=assessment.reasons,
            layers=assessment.layers,
            model_version=assessment.model_version,
            partial=assessment.partial,
            assessed_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        .on_conflict_do_update(
            index_elements=["job_id"],
            set_={
                "level": assessment.level,
                "score": assessment.score,
                "reasons": assessment.reasons,
                "layers": assessment.layers,
                "model_version": assessment.model_version,
                "partial": assessment.partial,
                "assessed_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            },
        )
        .returning(JobRisk)
    )
    row = (await ctx.session.execute(stmt)).scalar_one()
    await audit.record(
        ctx,
        action="safety.job_assessed",
        target_type="job",
        target_id=str(job_id),
        after={"level": assessment.level, "score": assessment.score, "partial": assessment.partial},
        actor_type="system",
    )
    await ctx.session.flush()
    return row


async def get_job_risk(ctx: WorkspaceContext, job_id: uuid.UUID) -> dict[str, Any]:
    row = await ctx.session.get(JobRisk, job_id)
    if row is None:
        raise AppError("not_found", "Risk not assessed", 404)
    override = (
        await ctx.session.execute(
            select(RiskOverride).where(
                RiskOverride.workspace_id == ctx.workspace_id,
                RiskOverride.job_id == job_id,
            )
        )
    ).scalar_one_or_none()
    return {
        "job_id": row.job_id,
        "level": row.level,
        "score": row.score,
        "reasons": row.reasons or [],
        "layers": row.layers or {},
        "model_version": row.model_version,
        "partial": row.partial,
        "assessed_at": row.assessed_at,
        "override": override.decision if override else None,
    }


async def decide(
    ctx: WorkspaceContext,
    job_id: uuid.UUID,
    *,
    decision: str,
    note: str = "",
    confirm_risk: bool = False,
) -> None:
    risk = await ctx.session.get(JobRisk, job_id)
    if risk is None:
        # Assess cheap layers first so the user can decide.
        risk = await assess_and_store(ctx, job_id, run_network=False, run_llm=False)

    if decision == "continue" and risk.level == "red" and not confirm_risk:
        raise AppError(
            "confirm_required",
            "Confirm that you understand this job is marked high risk before continuing",
            422,
        )

    existing = (
        await ctx.session.execute(
            select(RiskOverride).where(
                RiskOverride.workspace_id == ctx.workspace_id,
                RiskOverride.job_id == job_id,
            )
        )
    ).scalar_one_or_none()
    before = {"decision": existing.decision} if existing else None
    if existing:
        existing.decision = decision
        existing.note = note or ""
        existing.updated_at = datetime.now(UTC)
    else:
        ctx.session.add(
            RiskOverride(
                workspace_id=ctx.workspace_id,
                job_id=job_id,
                decision=decision,
                note=note or "",
            )
        )

    # Reported → hide track_jobs for this workspace.
    if decision in {"reported", "skip"}:
        tjs = (
            await ctx.session.execute(
                select(TrackJob).where(
                    TrackJob.workspace_id == ctx.workspace_id,
                    TrackJob.job_id == job_id,
                )
            )
        ).scalars()
        for tj in tjs:
            tj.status = "hidden" if decision == "reported" else "skipped"
            if decision == "skip":
                tj.skip_reason = tj.skip_reason or "risk"

    await audit.record(
        ctx,
        action="safety.risk_decision",
        target_type="job",
        target_id=str(job_id),
        before=before,
        after={"decision": decision},
    )
    await ctx.session.flush()

    # Re-assess so L7 community weight updates for this workspace's report.
    if decision == "reported":
        await assess_and_store(ctx, job_id, run_network=False, run_llm=False)


_MID_RUN_SIGNALS = frozenset(
    {
        "payment_request",
        "sensitive_data_ask",
        "chat_only_contact",
        "id_ask",
        "bank_ask",
        "takehome_malware_hint",
    }
)
_MID_RUN_MAX_WEIGHT = 25
_MID_RUN_MAX_SIGNALS = 5
_MID_RUN_MAX_TOTAL = 40


async def mid_run_signals(
    ctx: WorkspaceContext, job_id: uuid.UUID, signals: list[dict[str, Any]]
) -> JobRisk:
    """Runner/extension hook: payment request, sensitive asks mid-apply.

    Only for jobs linked in this workspace. Weights are allowlisted and capped so a
    client cannot force global red on arbitrary jobs.
    """
    linked = (
        await ctx.session.execute(
            select(TrackJob.id)
            .where(
                TrackJob.workspace_id == ctx.workspace_id,
                TrackJob.job_id == job_id,
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if linked is None:
        raise AppError("not_found", "Job not found", 404)

    normalized: list[dict[str, Any]] = []
    total = 0
    for s in (signals or [])[:_MID_RUN_MAX_SIGNALS]:
        name = str(s.get("signal") or "").strip()
        if name not in _MID_RUN_SIGNALS:
            continue
        w = max(0, min(_MID_RUN_MAX_WEIGHT, int(s.get("weight") or 20)))
        if total + w > _MID_RUN_MAX_TOTAL:
            w = max(0, _MID_RUN_MAX_TOTAL - total)
        if w <= 0:
            break
        total += w
        normalized.append(
            {
                "signal": name,
                "layer": "mid_run",
                "weight": w,
                "evidence": str(s.get("evidence") or "")[:200],
            }
        )
    row = await assess_and_store(
        ctx, job_id, run_network=False, run_llm=False, extra_signals=normalized or None
    )
    await audit.record(
        ctx,
        action="safety.mid_run_signal",
        target_type="job",
        target_id=str(job_id),
        after={"count": len(normalized), "level": row.level},
        actor_type="system",
    )
    return row


async def list_flagged(ctx: WorkspaceContext, *, limit: int = 50) -> list[dict[str, Any]]:
    q = (
        select(JobRisk, Job, TrackJob, RiskOverride)
        .join(Job, Job.id == JobRisk.job_id)
        .outerjoin(
            TrackJob,
            (TrackJob.job_id == JobRisk.job_id) & (TrackJob.workspace_id == ctx.workspace_id),
        )
        .outerjoin(
            RiskOverride,
            (RiskOverride.job_id == JobRisk.job_id)
            & (RiskOverride.workspace_id == ctx.workspace_id),
        )
        .where(JobRisk.level.in_(("yellow", "red")))
        .order_by(JobRisk.score.desc())
        .limit(limit)
    )
    rows = (await ctx.session.execute(q)).all()
    out: list[dict[str, Any]] = []
    seen: set[uuid.UUID] = set()
    for risk, job, tj, ov in rows:
        if job.id in seen:
            continue
        seen.add(job.id)
        company_name = None
        if job.company_id:
            from app.companies.models import Company

            c = await ctx.session.get(Company, job.company_id)
            company_name = c.name if c else None
        out.append(
            {
                "job_id": job.id,
                "track_job_id": tj.id if tj else None,
                "title": job.title,
                "company_name": company_name,
                "level": risk.level,
                "score": risk.score,
                "reasons": risk.reasons or [],
                "override": ov.decision if ov else None,
            }
        )
    return out


def run_check_this(*, text: str | None, url: str | None) -> dict[str, Any]:
    if url and url.strip():
        result = analyze_url(url.strip())
    elif text and text.strip():
        result = analyze_text(text.strip())
    else:
        raise AppError("bad_request", "Provide text or url", 422)
    return {
        "level": result.level,
        "score": result.score,
        "reasons": result.reasons,
        "advice": result.advice,
        "kind": result.kind,
    }


def classify_form_field(**kwargs: Any) -> dict[str, Any]:
    c = classify_field(**kwargs)
    return {
        "classification": c.classification,
        "reason": c.reason,
        "checkpoint": c.checkpoint,
    }
