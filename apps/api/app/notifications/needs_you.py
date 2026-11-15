"""Aggregate items that need human attention (Phase 11 Home consumes this)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.applications.models import Application, TailorRun
from app.core.security import WorkspaceContext
from app.extension.models import ApplyCheckpoint, ApplyRun
from app.jobs.models import DiscoveryRun, Job, TrackJob
from app.onboarding.models import SetupDraft
from app.onboarding.models import SetupDraft
from app.onboarding.models import SetupDraft
from app.onboarding.models import SetupDraft
from app.safety.models import JobRisk, RiskOverride


async def list_needs_you(ctx: WorkspaceContext, *, limit: int = 40) -> dict[str, Any]:
    items: list[dict[str, Any]] = []

    # Setup left answers only the person can give. One nudge per profile for 30 days.
    from datetime import timedelta

    cutoff = datetime.now(UTC) - timedelta(days=30)
    setup_rows = (
        (
            await ctx.session.execute(
                select(SetupDraft)
                .where(
                    SetupDraft.status == "applied",
                    SetupDraft.applied_at.is_not(None),
                    SetupDraft.applied_at >= cutoff,
                )
                .order_by(SetupDraft.applied_at.desc())
                .limit(10)
            )
        )
        .scalars()
        .all()
    )
    seen_profiles: set[Any] = set()
    for row in setup_rows:
        if row.profile_id in seen_profiles:
            continue
        seen_profiles.add(row.profile_id)
        count = int(((row.result or {}).get("counts") or {}).get("needs_you") or 0)
        if count <= 0:
            continue
        items.append(
            {
                "kind": "setup_answers",
                "title": f"{count} answers only you can give",
                "detail": "Open Answers and fill them in.",
                "href": "/profile/answers",
                "created_at": row.applied_at,
                "meta": {"draft_id": str(row.id), "profile_id": str(row.profile_id)},
            }
        )

    # Open apply-run checkpoints (Phase 15)
    open_cps = (
        await ctx.session.execute(
            select(ApplyCheckpoint, ApplyRun, Application)
            .join(ApplyRun, ApplyRun.id == ApplyCheckpoint.run_id)
            .outerjoin(Application, Application.id == ApplyRun.application_id)
            .where(
                ApplyCheckpoint.workspace_id == ctx.workspace_id,
                ApplyCheckpoint.status == "open",
            )
            .order_by(ApplyCheckpoint.created_at.desc())
            .limit(20)
        )
    ).all()
    for cp, run, app in open_cps:
        title = (app.job_title if app else None) or f"Apply run · {run.ats}"
        company = (app.company_name if app else None) or ""
        href = f"/applications/{app.id}" if app else "/applications"
        items.append(
            {
                "kind": "apply_checkpoint",
                "title": f"{title}" + (f" · {company}" if company else ""),
                "detail": f"Checkpoint: {cp.kind}",
                "href": href,
                "created_at": cp.created_at,
                "meta": {
                    "run_id": str(run.id),
                    "checkpoint_id": str(cp.id),
                    "kind": cp.kind,
                },
            }
        )

    # Answers setup could not fill: only the person can give them.
    setup_rows = list(
        (
            await ctx.session.execute(
                select(SetupDraft)
                .where(
                    SetupDraft.workspace_id == ctx.workspace_id,
                    SetupDraft.status == "applied",
                    SetupDraft.applied_at.is_not(None),
                )
                .order_by(SetupDraft.applied_at.desc())
                .limit(5)
            )
        ).scalars()
    )
    for row in setup_rows:
        count = int((row.result or {}).get("needs_you") or 0)
        if count <= 0:
            continue
        items.append(
            {
                "kind": "setup_answers",
                "title": f"{count} answer{'s' if count != 1 else ''} only you can give",
                "detail": "Work authorization, pay, or notice",
                "href": "/profile/answers",
                "created_at": row.applied_at,
                "meta": {"draft_id": str(row.id), "profile_id": str(row.profile_id)},
            }
        )

    # Answers setup could not fill: only the person can give them.
    setup_rows = list(
        (
            await ctx.session.execute(
                select(SetupDraft)
                .where(
                    SetupDraft.workspace_id == ctx.workspace_id,
                    SetupDraft.status == "applied",
                    SetupDraft.applied_at.is_not(None),
                )
                .order_by(SetupDraft.applied_at.desc())
                .limit(5)
            )
        ).scalars()
    )
    seen_profiles: set[str] = set()
    for row in setup_rows:
        if str(row.profile_id) in seen_profiles:
            continue
        seen_profiles.add(str(row.profile_id))
        count = int((row.result or {}).get("needs_you") or 0)
        if count <= 0:
            continue
        items.append(
            {
                "kind": "setup_answers",
                "title": f"{count} answer{'s' if count != 1 else ''} only you can give",
                "detail": "Work authorization, pay, or notice",
                "href": "/profile/answers",
                "created_at": row.applied_at,
                "meta": {"draft_id": str(row.id), "profile_id": str(row.profile_id)},
            }
        )

    # Answers setup could not fill: only the person can give them.
    setup_rows = list(
        (
            await ctx.session.execute(
                select(SetupDraft)
                .where(
                    SetupDraft.workspace_id == ctx.workspace_id,
                    SetupDraft.status == "applied",
                    SetupDraft.applied_at.is_not(None),
                )
                .order_by(SetupDraft.applied_at.desc())
                .limit(5)
            )
        ).scalars()
    )
    for row in setup_rows:
        count = int((row.result or {}).get("needs_you") or 0)
        if count <= 0:
            continue
        items.append(
            {
                "kind": "setup_answers",
                "title": f"{count} answer{'s' if count != 1 else ''} only you can give",
                "detail": "Work authorization, pay, or notice",
                "href": "/profile/answers",
                "created_at": row.applied_at,
                "meta": {"draft_id": str(row.id), "profile_id": str(row.profile_id)},
            }
        )

    # Answers setup could not fill: only the person can give them.
    setup_rows = list(
        (
            await ctx.session.execute(
                select(SetupDraft)
                .where(
                    SetupDraft.workspace_id == ctx.workspace_id,
                    SetupDraft.status == "applied",
                    SetupDraft.applied_at.is_not(None),
                )
                .order_by(SetupDraft.applied_at.desc())
                .limit(5)
            )
        ).scalars()
    )
    seen_profiles: set[str] = set()
    for row in setup_rows:
        if str(row.profile_id) in seen_profiles:
            continue
        seen_profiles.add(str(row.profile_id))
        count = int((row.result or {}).get("needs_you") or 0)
        if count <= 0:
            continue
        items.append(
            {
                "kind": "setup_answers",
                "title": f"{count} answer{'s' if count != 1 else ''} only you can give",
                "detail": "Work authorization, pay, or notice",
                "href": "/profile/answers",
                "created_at": row.applied_at,
                "meta": {"draft_id": str(row.id), "profile_id": str(row.profile_id)},
            }
        )

    # Answers that setup left for the person: eligibility, pay, or notice.
    from app.onboarding.models import SetupDraft

    setup_rows = (
        (
            await ctx.session.execute(
                select(SetupDraft)
                .where(
                    SetupDraft.workspace_id == ctx.workspace_id,
                    SetupDraft.status == "applied",
                    SetupDraft.applied_at.is_not(None),
                )
                .order_by(SetupDraft.applied_at.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )
    seen_profiles: set[str] = set()
    for row in setup_rows:
        if str(row.profile_id) in seen_profiles:
            continue
        seen_profiles.add(str(row.profile_id))
        count = int((row.result or {}).get("needs_you") or 0)
        if count <= 0:
            continue
        items.append(
            {
                "kind": "setup_answers",
                "title": f"{count} answer{'s' if count != 1 else ''} only you can give",
                "detail": "Work authorization, pay, or notice",
                "href": "/profile/answers",
                "created_at": row.applied_at,
                "meta": {"draft_id": str(row.id), "profile_id": str(row.profile_id)},
            }
        )

    # Answers setup could not fill: only the person can give them.
    setup_rows = list(
        (
            await ctx.session.execute(
                select(SetupDraft)
                .where(
                    SetupDraft.workspace_id == ctx.workspace_id,
                    SetupDraft.status == "applied",
                    SetupDraft.applied_at.is_not(None),
                )
                .order_by(SetupDraft.applied_at.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )
    seen_profiles: set[str] = set()
    for row in setup_rows:
        if str(row.profile_id) in seen_profiles:
            continue
        seen_profiles.add(str(row.profile_id))
        count = int((row.result or {}).get("needs_you") or 0)
        if count <= 0:
            continue
        items.append(
            {
                "kind": "setup_answers",
                "title": f"{count} answer{'s' if count != 1 else ''} only you can give",
                "detail": "Work authorization, pay, or notice",
                "href": "/profile/answers",
                "created_at": row.applied_at,
                "meta": {"draft_id": str(row.id), "profile_id": str(row.profile_id)},
            }
        )

    # Answers setup could not fill: only the person can give them.
    setup_rows = (
        (
            await ctx.session.execute(
                select(SetupDraft)
                .where(
                    SetupDraft.workspace_id == ctx.workspace_id,
                    SetupDraft.status == "applied",
                    SetupDraft.applied_at.is_not(None),
                )
                .order_by(SetupDraft.applied_at.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )
    seen_profiles: set[str] = set()
    for row in setup_rows:
        if str(row.profile_id) in seen_profiles:
            continue
        seen_profiles.add(str(row.profile_id))
        count = int((row.result or {}).get("needs_you") or 0)
        if count <= 0:
            continue
        items.append(
            {
                "kind": "setup_answers",
                "title": f"{count} answer{'s' if count != 1 else ''} only you can give",
                "detail": "Work authorization, pay, or notice",
                "href": "/profile/answers",
                "created_at": row.applied_at,
                "meta": {"draft_id": str(row.id)},
            }
        )

    # Answers setup could not fill: only the person can give them.
    setup_rows = list(
        (
            await ctx.session.execute(
                select(SetupDraft)
                .where(
                    SetupDraft.workspace_id == ctx.workspace_id,
                    SetupDraft.status == "applied",
                    SetupDraft.applied_at.is_not(None),
                )
                .order_by(SetupDraft.applied_at.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )
    seen_profiles: set[str] = set()
    for row in setup_rows:
        if str(row.profile_id) in seen_profiles:
            continue
        seen_profiles.add(str(row.profile_id))
        count = int((row.result or {}).get("needs_you") or 0)
        if count <= 0:
            continue
        items.append(
            {
                "kind": "setup_answers",
                "title": f"{count} answer{'s' if count != 1 else ''} only you can give",
                "detail": "Work authorization, pay, or notice",
                "href": "/profile/answers",
                "created_at": row.applied_at,
                "meta": {"draft_id": str(row.id)},
            }
        )

    # Tailor drafts waiting for review
    tailor_rows = (
        (
            await ctx.session.execute(
                select(TailorRun)
                .where(
                    TailorRun.workspace_id == ctx.workspace_id,
                    TailorRun.status == "ready",
                )
                .order_by(TailorRun.created_at.desc())
                .limit(20)
            )
        )
        .scalars()
        .all()
    )
    for row in tailor_rows:
        items.append(
            {
                "kind": "tailoring_review",
                "title": "Tailored draft ready",
                "detail": "Review and accept or discard",
                "href": f"/tailor/{row.track_job_id}",
                "created_at": row.created_at,
                "meta": {"tailor_run_id": str(row.id)},
            }
        )

    # Risk flags without override
    risk_rows = (
        await ctx.session.execute(
            select(JobRisk, Job, TrackJob)
            .join(Job, Job.id == JobRisk.job_id)
            .join(
                TrackJob,
                (TrackJob.job_id == JobRisk.job_id) & (TrackJob.workspace_id == ctx.workspace_id),
            )
            .outerjoin(
                RiskOverride,
                (RiskOverride.job_id == JobRisk.job_id)
                & (RiskOverride.workspace_id == ctx.workspace_id),
            )
            .where(
                JobRisk.level.in_(("yellow", "red")),
                RiskOverride.id.is_(None),
            )
            .order_by(JobRisk.score.desc())
            .limit(15)
        )
    ).all()
    for risk, job, tj in risk_rows:
        company = (job.meta or {}).get("company_name") if hasattr(job, "meta") else None
        company = company or "Company"
        items.append(
            {
                "kind": "risk_decision",
                "title": f"{job.title} · {company}",
                "detail": f"Risk {risk.level}",
                "href": f"/jobs?job={job.id}",
                "created_at": risk.assessed_at if hasattr(risk, "assessed_at") else None,
                "meta": {"job_id": str(job.id), "track_job_id": str(tj.id)},
            }
        )

    # Failed discovery runs (recent)
    failed = (
        (
            await ctx.session.execute(
                select(DiscoveryRun)
                .where(
                    DiscoveryRun.workspace_id == ctx.workspace_id,
                    DiscoveryRun.status == "failed",
                )
                .order_by(DiscoveryRun.created_at.desc())
                .limit(10)
            )
        )
        .scalars()
        .all()
    )
    for run in failed:
        items.append(
            {
                "kind": "failed_run",
                "title": "Discovery run failed",
                "detail": (run.error or "Unknown error")[:120],
                "href": f"/tracks/{run.track_id}/runs",
                "created_at": run.finished_at or run.created_at,
                "meta": {"run_id": str(run.id)},
            }
        )

    # Budget reached (from recent notifications)
    from app.notifications.models import Notification

    budget = (
        (
            await ctx.session.execute(
                select(Notification)
                .where(
                    Notification.workspace_id == ctx.workspace_id,
                    Notification.user_id == ctx.user_id,
                    Notification.type == "budget_reached",
                    Notification.read_at.is_(None),
                )
                .order_by(Notification.created_at.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )
    for n in budget:
        items.append(
            {
                "kind": "budget_reached",
                "title": n.title or "Budget reached",
                "detail": n.body or "",
                "href": "/settings/ai",
                "created_at": n.created_at,
                "meta": {},
            }
        )

    items.sort(
        key=lambda x: x.get("created_at") or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )
    items = items[:limit]
    return {"count": len(items), "items": items}
