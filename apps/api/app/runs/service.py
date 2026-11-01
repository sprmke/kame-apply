"""Apply-run lifecycle: preflight, queue, checkpoints, step log, handoff."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.applications import status as app_status
from app.applications.models import Application
from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.extension import models as m
from app.jobs.models import Job
from app.notifications import service as notif
from app.resumes.models import ResumeVersion
from app.runs.ats import NO_AUTO_SUBMIT, detect_ats
from app.runs.tokens import hash_token, new_runner_token
from app.safety.models import JobRisk, RiskOverride
from app.tracks.models import Track


def _now() -> datetime:
    return datetime.now(UTC)


def _set_app_status(app: Application, new: str) -> None:
    app_status.assert_transition(app.status, new)
    app.status = app_status.normalize(new)


async def _notify(
    ctx: WorkspaceContext, *, event: str, title: str, body: str, href: str, meta: dict
) -> None:
    await notif.emit(
        ctx,
        user_id=ctx.user_id,
        event=event,
        title=title,
        body=body,
        payload={**meta, "href": href},
        dedupe_key=f"{event}:{meta.get('run_id') or meta.get('checkpoint_id') or title}",
    )


async def create_runner_token(
    ctx: WorkspaceContext, *, label: str, mode: str
) -> tuple[m.RunnerToken, str]:
    raw = new_runner_token()
    row = m.RunnerToken(
        workspace_id=ctx.workspace_id,
        user_id=ctx.user_id,
        token_hash=hash_token(raw),
        label=label.strip() or mode,
        mode=mode,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="runner.token_created",
        target_type="runner_token",
        target_id=str(row.id),
        after={"mode": mode, "label": row.label},
    )
    return row, raw


async def list_runner_tokens(ctx: WorkspaceContext) -> list[m.RunnerToken]:
    return list(
        (
            await ctx.session.execute(
                select(m.RunnerToken)
                .where(m.RunnerToken.revoked_at.is_(None))
                .order_by(m.RunnerToken.created_at.desc())
            )
        ).scalars()
    )


async def revoke_runner_token(ctx: WorkspaceContext, token_id: uuid.UUID) -> None:
    row = await ctx.session.get(m.RunnerToken, token_id)
    if row is None or row.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Runner token not found", 404)
    row.revoked_at = _now()
    await audit.record(
        ctx, action="runner.token_revoked", target_type="runner_token", target_id=str(token_id)
    )


async def _get_application(ctx: WorkspaceContext, application_id: uuid.UUID) -> Application:
    app = await ctx.session.get(Application, application_id)
    if app is None or app.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Application not found", 404)
    return app


async def preflight(ctx: WorkspaceContext, app: Application) -> dict[str, Any]:
    """Validate risk, resume, job open, caps. Returns policy snapshot."""
    if app.status not in {"ready", "in_progress", "needs_you"}:
        raise AppError("invalid_status", "Application is not ready for the runner", 409)

    job = await ctx.session.get(Job, app.job_id)
    if job is None or job.status == "closed":
        raise AppError("job_closed", "This job is no longer open", 409)

    track = await ctx.session.get(Track, app.track_id)
    if track is None:
        raise AppError("not_found", "Track not found", 404)

    risk = (
        await ctx.session.execute(select(JobRisk).where(JobRisk.job_id == app.job_id))
    ).scalar_one_or_none()
    override = (
        await ctx.session.execute(
            select(RiskOverride).where(
                RiskOverride.workspace_id == ctx.workspace_id, RiskOverride.job_id == app.job_id
            )
        )
    ).scalar_one_or_none()
    if risk and risk.level == "red" and override is None:
        raise AppError("risk_blocked", "Acknowledge the risk before applying", 409)

    resume_ok = False
    if app.resume_version_id:
        rv = await ctx.session.get(ResumeVersion, app.resume_version_id)
        resume_ok = bool(rv and (rv.r2_pdf or rv.r2_docx or rv.content))
    if not resume_ok:
        # Base resume on track
        raise AppError("docs_required", "Attach an accepted resume before applying", 409)

    apply_url = app.apply_url or (job.apply_url if job else "") or ""
    if not apply_url:
        raise AppError("no_apply_url", "No apply URL on this application", 409)

    from app.strategy import service as strategy_svc

    cap = await strategy_svc.company_cap_for_application(ctx, app.id)
    if cap.exceeds:
        raise AppError(
            "company_cap",
            cap.message,
            409,
        )

    ats = detect_ats(apply_url)
    allow_submit_requested = False  # set by start()
    freshness = None
    if job:
        from app.strategy.freshness import freshness_for

        freshness = freshness_for(
            job_id=job.id, posted_at=job.posted_at, first_seen_at=job.first_seen_at
        ).model_dump(mode="json")
    return {
        "ats": ats,
        "apply_url": apply_url,
        "track_autonomy": track.autonomy,
        "risk_level": risk.level if risk else "green",
        "allow_submit": False,
        "platform_no_auto_submit": ats in NO_AUTO_SUBMIT,
        "allow_submit_requested": allow_submit_requested,
        "company_cap": cap.model_dump(mode="json"),
        "freshness": freshness,
    }


async def start_runner(
    ctx: WorkspaceContext,
    *,
    application_id: uuid.UUID,
    allow_submit: bool,
    settings: Any | None = None,
) -> m.ApplyRun:
    app = await _get_application(ctx, application_id)
    policy = await preflight(ctx, app)
    # Never allow auto-submit on restricted platforms; assist still needs final_review approval.
    if policy["platform_no_auto_submit"]:
        allow_submit = False

    # Phase 19: evaluate auto-submit policy when track asks for it.
    auto_verdict = None
    if track_autonomy := policy.get("track_autonomy"):
        if track_autonomy == "auto_submit" and settings is not None:
            from app.autosubmit import service as autosubmit_svc

            auto_verdict = await autosubmit_svc.evaluate_for_application(
                ctx, application_id, settings=settings
            )
            policy["auto_submit"] = auto_verdict.model_dump(mode="json")
            if auto_verdict.allow_submit:
                allow_submit = True
            elif auto_verdict.dry_run:
                allow_submit = False
            else:
                allow_submit = False

    policy["allow_submit"] = bool(allow_submit)
    policy["allow_submit_requested"] = bool(allow_submit)

    run = m.ApplyRun(
        workspace_id=ctx.workspace_id,
        application_id=app.id,
        job_id=app.job_id,
        track_id=app.track_id,
        profile_id=app.profile_id,
        source="runner",
        platform=policy["ats"],
        ats=policy["ats"],
        page_url=policy["apply_url"],
        status="queued",
        policy=policy,
        submit_approved=False,
        created_by=ctx.user_id,
    )
    ctx.session.add(run)
    await ctx.session.flush()

    if auto_verdict and auto_verdict.dry_run:
        from app.autosubmit import service as autosubmit_svc

        await autosubmit_svc.record_dry_run(
            ctx,
            track_id=app.track_id,
            application_id=app.id,
            run_id=run.id,
            verdict=auto_verdict,
        )

    if app.status == "ready":
        _set_app_status(app, "in_progress")

    await audit.record(
        ctx,
        action="apply_run.queued",
        target_type="apply_run",
        target_id=str(run.id),
        after={"application_id": str(app.id), "ats": policy["ats"]},
    )
    await _notify(
        ctx,
        event="needs_review",
        title="Apply run queued",
        body=f"{app.job_title} · {app.company_name}",
        href=f"/applications/{app.id}",
        meta={"run_id": str(run.id)},
    )
    return run


async def get_run(ctx: WorkspaceContext, run_id: uuid.UUID) -> m.ApplyRun:
    run = await ctx.session.get(m.ApplyRun, run_id)
    if run is None or run.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Run not found", 404)
    return run


async def list_runs(
    ctx: WorkspaceContext, *, application_id: uuid.UUID | None = None
) -> list[m.ApplyRun]:
    q = select(m.ApplyRun).order_by(m.ApplyRun.created_at.desc()).limit(50)
    if application_id is not None:
        q = q.where(m.ApplyRun.application_id == application_id)
    return list((await ctx.session.execute(q)).scalars())


async def list_steps(ctx: WorkspaceContext, run_id: uuid.UUID) -> list[m.ApplyRunStep]:
    await get_run(ctx, run_id)
    return list(
        (
            await ctx.session.execute(
                select(m.ApplyRunStep)
                .where(m.ApplyRunStep.run_id == run_id)
                .order_by(m.ApplyRunStep.seq)
            )
        ).scalars()
    )


async def list_checkpoints(ctx: WorkspaceContext, run_id: uuid.UUID) -> list[m.ApplyCheckpoint]:
    await get_run(ctx, run_id)
    return list(
        (
            await ctx.session.execute(
                select(m.ApplyCheckpoint)
                .where(m.ApplyCheckpoint.run_id == run_id)
                .order_by(m.ApplyCheckpoint.created_at)
            )
        ).scalars()
    )


async def claim_next(ctx: WorkspaceContext, *, runner_id: str) -> m.ApplyRun | None:
    """Runner pulls the oldest queued run for this workspace."""
    run = (
        await ctx.session.execute(
            select(m.ApplyRun)
            .where(m.ApplyRun.status == "queued", m.ApplyRun.source == "runner")
            .order_by(m.ApplyRun.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
    ).scalar_one_or_none()
    if run is None:
        return None
    run.status = "running"
    run.runner_id = runner_id
    run.started_at = run.started_at or _now()
    run.heartbeat_at = _now()
    run.updated_at = _now()
    await audit.record(
        ctx,
        action="apply_run.claimed",
        target_type="apply_run",
        target_id=str(run.id),
        after={"runner_id": runner_id},
        actor_type="system",
    )
    return run


async def heartbeat(
    ctx: WorkspaceContext, run_id: uuid.UUID, *, runner_id: str, page_url: str | None
) -> m.ApplyRun:
    run = await get_run(ctx, run_id)
    if run.runner_id and run.runner_id != runner_id:
        raise AppError("forbidden", "Another runner owns this run", 403)
    run.heartbeat_at = _now()
    run.runner_id = runner_id
    if page_url:
        run.page_url = page_url
    run.updated_at = _now()
    return run


async def append_step(
    ctx: WorkspaceContext, run_id: uuid.UUID, body: dict[str, Any]
) -> m.ApplyRunStep:
    run = await get_run(ctx, run_id)
    # Idempotent: same seq replaces nothing; skip if exists
    existing = (
        await ctx.session.execute(
            select(m.ApplyRunStep).where(
                m.ApplyRunStep.run_id == run_id, m.ApplyRunStep.seq == body["seq"]
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    step = m.ApplyRunStep(
        workspace_id=ctx.workspace_id,
        run_id=run_id,
        seq=body["seq"],
        page_url=body.get("page_url") or "",
        action=body.get("action") or "fill",
        field_label=body.get("field_label") or "",
        value_redacted=body.get("value_redacted") or "",
        canonical_key=body.get("canonical_key"),
        source_fact_ref=body.get("source_fact_ref"),
        pii_class=body.get("pii_class") or "personal",
        screenshot_r2=body.get("screenshot_r2"),
        outcome=body.get("outcome") or "ok",
    )
    ctx.session.add(step)
    run.last_step_seq = max(run.last_step_seq, body["seq"])
    run.updated_at = _now()
    await ctx.session.flush()
    return step


async def open_checkpoint(
    ctx: WorkspaceContext, run_id: uuid.UUID, *, kind: str, detail: dict[str, Any]
) -> m.ApplyCheckpoint:
    run = await get_run(ctx, run_id)
    # One open checkpoint of the same kind for same field label is enough
    cp = m.ApplyCheckpoint(
        workspace_id=ctx.workspace_id,
        run_id=run_id,
        kind=kind,
        detail=detail or {},
        status="open",
    )
    ctx.session.add(cp)
    run.status = "needs_you"
    # Checkpoints switch control to HUMAN automatically (Phase 16).
    run.control_mode = "human"
    if run.live_mode == "off":
        run.live_mode = "screencast"
    run.updated_at = _now()
    await ctx.session.flush()

    if run.application_id:
        app = await ctx.session.get(Application, run.application_id)
        if app and app.status == "in_progress":
            _set_app_status(app, "needs_you")

    await _notify(
        ctx,
        event="needs_review",
        title=f"Checkpoint: {kind}",
        body=str(detail.get("label") or detail.get("message") or kind)[:120],
        href=f"/applications/{run.application_id}" if run.application_id else "/applications",
        meta={"run_id": str(run_id), "checkpoint_id": str(cp.id), "kind": kind},
    )
    await audit.record(
        ctx,
        action="apply_checkpoint.opened",
        target_type="checkpoint",
        target_id=str(cp.id),
        after={"kind": kind},
        actor_type="system",
    )
    return cp


async def resolve_checkpoint(
    ctx: WorkspaceContext,
    checkpoint_id: uuid.UUID,
    *,
    decision: str,
    value: str | None,
    note: str | None,
) -> m.ApplyCheckpoint:
    cp = await ctx.session.get(m.ApplyCheckpoint, checkpoint_id)
    if cp is None or cp.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Checkpoint not found", 404)
    if cp.status != "open":
        raise AppError("invalid_status", "Checkpoint is not open", 409)

    run = await get_run(ctx, cp.run_id)
    payload: dict[str, Any] = {"decision": decision, "note": note}
    # Sensitive typed values are never stored on the checkpoint row.
    if decision == "typed_value" and cp.kind == "sensitive_field":
        payload["value_present"] = bool(value)
        # Ephemeral: stash on run.policy for one-shot runner pickup, then clear on next heartbeat
        # after use. Never write the raw value into activity_log or checkpoint.decision.
        ephemeral = dict(run.policy or {})
        ephemeral["_ephemeral_sensitive"] = {
            "checkpoint_id": str(cp.id),
            "value": value or "",
        }
        run.policy = ephemeral
    elif decision == "typed_value":
        payload["value"] = value
    elif decision == "approve_submit":
        if run.policy.get("platform_no_auto_submit"):
            raise AppError("submit_forbidden", "This platform cannot be auto-submitted", 409)
        if not run.policy.get("allow_submit"):
            # User's explicit final_review approval is the click even when track policy is assist.
            pass
        run.submit_approved = True
    elif decision == "deny_submit":
        run.submit_approved = False
    elif decision == "cancel":
        run.status = "cancelled"
        run.ended_at = _now()
    elif decision == "handoff_extension":
        run.status = "paused"
        payload["handoff"] = True

    cp.status = "resolved"
    cp.decision = {k: v for k, v in payload.items() if k != "value" or cp.kind != "sensitive_field"}
    if cp.kind == "sensitive_field" and decision == "typed_value":
        cp.decision = {"decision": decision, "value_present": True, "note": note}
    cp.decided_by = ctx.user_id
    cp.decided_at = _now()

    if run.status == "needs_you" and decision not in {"cancel", "handoff_extension"}:
        run.status = "running"
        run.control_mode = "agent"
        run.controller_user_id = None
        if run.application_id:
            app = await ctx.session.get(Application, run.application_id)
            if app and app.status == "needs_you":
                _set_app_status(app, "in_progress")

    run.updated_at = _now()
    await audit.record(
        ctx,
        action="apply_checkpoint.resolved",
        target_type="checkpoint",
        target_id=str(cp.id),
        after={"decision": decision, "kind": cp.kind},
    )

    # DBOS send when configured
    try:
        from app.runs.workflow import send_checkpoint_decision

        send_checkpoint_decision(str(cp.id), decision)
    except Exception:  # noqa: S110 — DBOS optional in tests
        pass

    return cp


async def complete_run(
    ctx: WorkspaceContext,
    run_id: uuid.UUID,
    *,
    status: str,
    failure_reason: str | None = None,
    confirmation: bool = False,
) -> m.ApplyRun:
    run = await get_run(ctx, run_id)
    if status == "completed":
        # Never mark submitted unless final_review approved submit.
        if confirmation:
            if not run.submit_approved:
                raise AppError(
                    "submit_not_approved",
                    "Submit requires final review approval",
                    409,
                )
            if run.application_id:
                app = await ctx.session.get(Application, run.application_id)
                if app and app.status in {"in_progress", "needs_you", "ready"}:
                    _set_app_status(app, "submitted")
                    app.method = "runner"
                    app.submitted_at = _now()
        run.status = "completed"
    elif status in {"failed", "cancelled"}:
        run.status = status
        run.failure_reason = failure_reason
    else:
        raise AppError("bad_request", "Invalid completion status", 400)
    run.ended_at = _now()
    run.updated_at = _now()
    await audit.record(
        ctx,
        action=f"apply_run.{status}",
        target_type="apply_run",
        target_id=str(run_id),
        after={"confirmation": confirmation, "failure_reason": failure_reason},
        actor_type="system",
    )
    return run


async def handoff(ctx: WorkspaceContext, run_id: uuid.UUID) -> dict[str, Any]:
    run = await get_run(ctx, run_id)
    open_cp = (
        await ctx.session.execute(
            select(m.ApplyCheckpoint)
            .where(m.ApplyCheckpoint.run_id == run_id, m.ApplyCheckpoint.status == "open")
            .order_by(m.ApplyCheckpoint.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    run.status = "paused"
    run.updated_at = _now()
    await audit.record(
        ctx,
        action="apply_run.handoff_extension",
        target_type="apply_run",
        target_id=str(run_id),
    )
    return {
        "url": run.page_url,
        "run_id": run.id,
        "last_step_seq": run.last_step_seq,
        "open_checkpoint_id": open_cp.id if open_cp else None,
    }


async def pop_ephemeral_sensitive(ctx: WorkspaceContext, run_id: uuid.UUID) -> str | None:
    """Runner reads one-shot sensitive value; cleared immediately."""
    run = await get_run(ctx, run_id)
    policy = dict(run.policy or {})
    blob = policy.pop("_ephemeral_sensitive", None)
    run.policy = policy
    if not blob:
        return None
    return str(blob.get("value") or "") or None


def run_to_read(run: m.ApplyRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "application_id": run.application_id,
        "job_id": run.job_id,
        "track_id": run.track_id,
        "profile_id": run.profile_id,
        "status": run.status,
        "source": run.source,
        "ats": run.ats,
        "page_url": run.page_url,
        "platform": run.platform,
        "policy": {k: v for k, v in (run.policy or {}).items() if not k.startswith("_")},
        "submit_approved": run.submit_approved,
        "failure_reason": run.failure_reason,
        "last_step_seq": run.last_step_seq,
        "runner_id": run.runner_id,
        "control_mode": getattr(run, "control_mode", None) or "agent",
        "live_mode": getattr(run, "live_mode", None) or "off",
        "controller_user_id": getattr(run, "controller_user_id", None),
        "user_edited_fields": list(getattr(run, "user_edited_fields", None) or []),
        "live_telemetry": dict(getattr(run, "live_telemetry", None) or {}),
        "started_at": run.started_at,
        "ended_at": run.ended_at,
        "heartbeat_at": run.heartbeat_at,
        "created_at": run.created_at,
    }


async def set_control_mode(
    ctx: WorkspaceContext,
    run_id: uuid.UUID,
    *,
    mode: str,
    controller_user_id: uuid.UUID | None = None,
) -> m.ApplyRun:
    run = await get_run(ctx, run_id)
    if mode not in {"agent", "human", "paused"}:
        raise AppError("bad_request", "Invalid control mode", 400)
    run.control_mode = mode
    run.controller_user_id = controller_user_id if mode == "human" else None
    run.updated_at = _now()
    await audit.record(
        ctx,
        action=f"apply_run.control_{mode}",
        target_type="apply_run",
        target_id=str(run_id),
        after={"controller_user_id": str(controller_user_id) if controller_user_id else None},
    )
    return run


async def set_live_mode(ctx: WorkspaceContext, run_id: uuid.UUID, *, live_mode: str) -> m.ApplyRun:
    run = await get_run(ctx, run_id)
    if live_mode not in {"off", "screencast", "screenshot"}:
        raise AppError("bad_request", "Invalid live mode", 400)
    run.live_mode = live_mode
    run.updated_at = _now()
    return run


async def lock_user_edited_field(
    ctx: WorkspaceContext, run_id: uuid.UUID, *, field_id: str, label: str
) -> m.ApplyRun:
    run = await get_run(ctx, run_id)
    locks = list(run.user_edited_fields or [])
    if not any(x.get("field_id") == field_id for x in locks if isinstance(x, dict)):
        locks.append({"field_id": field_id, "label": label})
        run.user_edited_fields = locks
        run.updated_at = _now()
    return run


async def update_live_telemetry(
    ctx: WorkspaceContext, run_id: uuid.UUID, telemetry: dict[str, Any]
) -> m.ApplyRun:
    run = await get_run(ctx, run_id)
    cur = dict(run.live_telemetry or {})
    cur.update(telemetry)
    run.live_telemetry = cur
    run.updated_at = _now()
    return run
