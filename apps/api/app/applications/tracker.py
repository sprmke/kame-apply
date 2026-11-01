"""Applications tracker: list/detail/status/manual log/snapshot/reminders/export."""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select

from app.applications import status as sm
from app.applications.follow_up import draft_follow_up
from app.applications.models import (
    Application,
    ApplicationEvent,
    ApplicationReminder,
    ApplicationSavedView,
)
from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.jobs.models import Job, TrackJob
from app.jobs.normalize import normalize_title
from app.tracks import models as track_models


def _grade_from_lens(lens: dict[str, Any] | None) -> str:
    if not lens:
        return ""
    return str(lens.get("grade") or lens.get("letter") or "")[:8]


def _app_dict(
    app: Application,
    *,
    job: Job | None = None,
    events: list[ApplicationEvent] | None = None,
    reminders: list[ApplicationReminder] | None = None,
    duplicate_warning: bool = False,
) -> dict[str, Any]:
    title = app.job_title or (job.title if job else "")
    company = app.company_name or ((job.meta or {}).get("company_name") if job else "") or ""
    return {
        "id": app.id,
        "track_id": app.track_id,
        "job_id": app.job_id,
        "track_job_id": app.track_job_id,
        "profile_id": app.profile_id,
        "status": sm.normalize(app.status),
        "method": app.method,
        "resume_version_id": app.resume_version_id,
        "cover_letter_id": app.cover_letter_id,
        "job_snapshot_r2": app.job_snapshot_r2,
        "lens_before": app.lens_before or {},
        "lens_after": app.lens_after or {},
        "notes": app.notes or "",
        "company_name": company,
        "job_title": title,
        "apply_url": app.apply_url or (job.apply_url if job else "") or "",
        "follow_up_draft": app.follow_up_draft or "",
        "reminder_days": app.reminder_days,
        "reminder_at": app.reminder_at,
        "responded_at": app.responded_at,
        "interview_at": app.interview_at,
        "outcome_at": app.outcome_at,
        "ghosted_suggested_at": app.ghosted_suggested_at,
        "tailored": bool(app.tailored),
        "lens_grade": app.lens_grade or _grade_from_lens(app.lens_after),
        "source_key": app.source_key or "",
        "created_at": app.created_at,
        "submitted_at": app.submitted_at,
        "updated_at": app.updated_at,
        "duplicate_warning": duplicate_warning,
        "events": [
            {
                "id": e.id,
                "type": e.type,
                "payload": e.payload or {},
                "note": e.note or "",
                "at": e.at,
                "actor_type": e.actor_type,
            }
            for e in (events or [])
        ],
        "reminders": [
            {
                "id": r.id,
                "kind": r.kind,
                "due_at": r.due_at,
                "done_at": r.done_at,
                "draft": r.draft or "",
            }
            for r in (reminders or [])
        ],
    }


async def _add_event(
    ctx: WorkspaceContext,
    app: Application,
    *,
    type: str,
    payload: dict[str, Any] | None = None,
    note: str = "",
) -> ApplicationEvent:
    ev = ApplicationEvent(
        workspace_id=ctx.workspace_id,
        application_id=app.id,
        type=type,
        payload=payload or {},
        note=note,
        actor_type="user",
        actor_id=str(ctx.user_id) if ctx.user_id else None,
    )
    ctx.session.add(ev)
    return ev


async def write_job_snapshot(
    ctx: WorkspaceContext, app: Application, job: Job, storage: Any
) -> str | None:
    if storage is None:
        return None
    key = f"ws/{ctx.workspace_id}/applications/{app.id}/job-snapshot.json"
    payload = {
        "title": job.title,
        "company": (job.meta or {}).get("company_name"),
        "apply_url": job.apply_url,
        "canonical_url": job.canonical_url,
        "description_html": job.description_html or "",
        "description_text": job.description_text or "",
        "locations": job.locations or [],
        "salary": job.salary or {},
        "skills": job.skills or [],
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        "captured_at": datetime.now(UTC).isoformat(),
    }
    body = json.dumps(payload, ensure_ascii=False).encode()
    await storage.put(key, body, "application/json")
    app.job_snapshot_r2 = key
    return key


async def check_duplicate(
    ctx: WorkspaceContext, *, job_id: uuid.UUID, exclude_app_id: uuid.UUID | None = None
) -> Application | None:
    q = select(Application).where(
        Application.workspace_id == ctx.workspace_id,
        Application.job_id == job_id,
        Application.status.notin_(("withdrawn", "draft")),
    )
    if exclude_app_id:
        q = q.where(Application.id != exclude_app_id)
    return (await ctx.session.execute(q.limit(1))).scalar_one_or_none()


async def list_applications(
    ctx: WorkspaceContext,
    *,
    track_id: uuid.UUID | None = None,
    status: str | None = None,
    method: str | None = None,
    q: str | None = None,
    submitted_from: datetime | None = None,
    submitted_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    filters = [Application.workspace_id == ctx.workspace_id]
    if track_id:
        filters.append(Application.track_id == track_id)
    if status:
        filters.append(Application.status == sm.normalize(status))
    if method:
        filters.append(Application.method == method)
    if submitted_from:
        filters.append(Application.submitted_at >= submitted_from)
    if submitted_to:
        filters.append(Application.submitted_at <= submitted_to)
    if q:
        like = f"%{q.strip()}%"
        filters.append(or_(Application.company_name.ilike(like), Application.job_title.ilike(like)))

    total = int(
        (
            await ctx.session.execute(
                select(func.count()).select_from(Application).where(and_(*filters))
            )
        ).scalar_one()
    )
    rows = (
        await ctx.session.execute(
            select(Application, Job)
            .outerjoin(Job, Job.id == Application.job_id)
            .where(and_(*filters))
            .order_by(Application.updated_at.desc())
            .limit(min(limit, 200))
            .offset(max(offset, 0))
        )
    ).all()
    items = []
    for app, job in rows:
        dup = False
        if job:
            other = await check_duplicate(ctx, job_id=job.id, exclude_app_id=app.id)
            dup = other is not None
        items.append(_app_dict(app, job=job, duplicate_warning=dup))
    return {"total": total, "items": items, "limit": limit, "offset": offset}


async def get_application_detail(ctx: WorkspaceContext, app_id: uuid.UUID) -> dict[str, Any]:
    app = await ctx.session.get(Application, app_id)
    if app is None or app.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Application not found", 404)
    await ctx.session.refresh(app)
    job = await ctx.session.get(Job, app.job_id)
    events = list(
        (
            await ctx.session.execute(
                select(ApplicationEvent)
                .where(ApplicationEvent.application_id == app.id)
                .order_by(ApplicationEvent.at.asc())
            )
        )
        .scalars()
        .all()
    )
    reminders = list(
        (
            await ctx.session.execute(
                select(ApplicationReminder)
                .where(ApplicationReminder.application_id == app.id)
                .order_by(ApplicationReminder.due_at.asc())
            )
        )
        .scalars()
        .all()
    )
    dup = False
    if job:
        other = await check_duplicate(ctx, job_id=job.id, exclude_app_id=app.id)
        dup = other is not None
    out = _app_dict(app, job=job, events=events, reminders=reminders, duplicate_warning=dup)
    if job:
        out["job"] = {
            "id": job.id,
            "title": job.title,
            "status": job.status,
            "description_text": job.description_text or "",
            "apply_url": job.apply_url,
            "canonical_url": job.canonical_url,
            "company_name": (job.meta or {}).get("company_name"),
        }
    return out


async def update_status(
    ctx: WorkspaceContext,
    app_id: uuid.UUID,
    *,
    status: str,
    note: str = "",
    storage: Any = None,
) -> dict[str, Any]:
    app = await ctx.session.get(Application, app_id)
    if app is None or app.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Application not found", 404)
    new = sm.normalize(status)
    sm.assert_transition(app.status, new, note=note)
    before = sm.normalize(app.status)
    app.status = new
    now = datetime.now(UTC)
    if new == "submitted" and not app.submitted_at:
        app.submitted_at = now
        app.reminder_at = now + timedelta(days=app.reminder_days or 7)
        if not app.follow_up_draft:
            app.follow_up_draft = draft_follow_up(company=app.company_name, title=app.job_title)
        ctx.session.add(
            ApplicationReminder(
                workspace_id=ctx.workspace_id,
                application_id=app.id,
                kind="follow_up",
                due_at=app.reminder_at,
                draft=app.follow_up_draft,
            )
        )
        job = await ctx.session.get(Job, app.job_id)
        if job and storage:
            await write_job_snapshot(ctx, app, job, storage)
    if new == "responded":
        app.responded_at = now
    if new == "interview":
        app.interview_at = now
    if new in {"offer", "rejected", "withdrawn"}:
        app.outcome_at = now
    await _add_event(
        ctx,
        app,
        type="status_change",
        payload={"from": before, "to": new},
        note=note,
    )
    await audit.record(
        ctx,
        action="application.status_changed",
        target_type="application",
        target_id=str(app.id),
        before={"status": before},
        after={"status": new},
    )
    await ctx.session.flush()
    return await get_application_detail(ctx, app.id)


async def update_notes(ctx: WorkspaceContext, app_id: uuid.UUID, notes: str) -> dict[str, Any]:
    app = await ctx.session.get(Application, app_id)
    if app is None or app.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Application not found", 404)
    app.notes = notes
    await _add_event(ctx, app, type="note", note=notes[:200])
    await audit.record(
        ctx,
        action="application.notes_updated",
        target_type="application",
        target_id=str(app.id),
    )
    await ctx.session.flush()
    return await get_application_detail(ctx, app.id)


async def mark_applied_from_job(
    ctx: WorkspaceContext,
    *,
    track_job_id: uuid.UUID | None = None,
    job_id: uuid.UUID | None = None,
    track_id: uuid.UUID | None = None,
    method: str = "manual",
    notes: str = "",
    storage: Any = None,
) -> dict[str, Any]:
    """Two-click 'I applied on the company site' from a TrackJob or job+track."""
    tj: TrackJob | None = None
    if track_job_id:
        tj = await ctx.session.get(TrackJob, track_job_id)
        if tj is None or tj.workspace_id != ctx.workspace_id:
            raise AppError("not_found", "Track job not found", 404)
        job_id = tj.job_id
        track_id = tj.track_id
    if not job_id or not track_id:
        raise AppError("validation_error", "job_id and track_id required", 422)

    track = await ctx.session.get(track_models.Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track not found", 404)
    job = await ctx.session.get(Job, job_id)
    if job is None:
        raise AppError("not_found", "Job not found", 404)

    dup = await check_duplicate(ctx, job_id=job.id)
    existing = (
        await ctx.session.execute(
            select(Application).where(
                Application.workspace_id == ctx.workspace_id,
                Application.track_id == track_id,
                Application.job_id == job.id,
            )
        )
    ).scalar_one_or_none()

    company = (job.meta or {}).get("company_name") or ""
    if existing:
        app = existing
        if sm.normalize(app.status) not in {"submitted", "responded", "interview", "offer"}:
            sm.assert_transition(app.status, "submitted", note=notes)
            app.status = "submitted"
            app.submitted_at = datetime.now(UTC)
    else:
        app = Application(
            workspace_id=ctx.workspace_id,
            track_id=track_id,
            job_id=job.id,
            track_job_id=tj.id if tj else None,
            profile_id=track.profile_id,
            status="submitted",
            method=method,
            notes=notes,
            company_name=company,
            job_title=job.title,
            apply_url=job.apply_url or job.canonical_url or "",
            tailored=False,
            submitted_at=datetime.now(UTC),
        )
        ctx.session.add(app)
        await ctx.session.flush()

    app.company_name = company or app.company_name
    app.job_title = job.title
    app.apply_url = job.apply_url or job.canonical_url or app.apply_url
    app.method = method
    if notes:
        app.notes = notes
    app.reminder_days = 7
    app.reminder_at = datetime.now(UTC) + timedelta(days=7)
    app.follow_up_draft = draft_follow_up(company=app.company_name, title=app.job_title)
    ctx.session.add(
        ApplicationReminder(
            workspace_id=ctx.workspace_id,
            application_id=app.id,
            kind="follow_up",
            due_at=app.reminder_at,
            draft=app.follow_up_draft,
        )
    )
    if storage:
        await write_job_snapshot(ctx, app, job, storage)
    await _add_event(
        ctx,
        app,
        type="submitted",
        payload={"method": method, "duplicate_warning": dup is not None},
        note=notes,
    )
    if tj and tj.status not in {"applied", "hidden"}:
        tj.status = "applied"
    await audit.record(
        ctx,
        action="application.marked_applied",
        target_type="application",
        target_id=str(app.id),
        after={"job_id": str(job.id), "method": method},
    )
    await ctx.session.flush()
    detail = await get_application_detail(ctx, app.id)
    detail["duplicate_warning"] = dup is not None
    return detail


async def create_manual(
    ctx: WorkspaceContext,
    *,
    track_id: uuid.UUID,
    company: str,
    title: str,
    url: str = "",
    method: str = "manual",
    notes: str = "",
    mark_submitted: bool = True,
) -> dict[str, Any]:
    track = await ctx.session.get(track_models.Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track not found", 404)
    # Stub job so FK + corpus stay consistent
    content_hash = f"manual-{uuid.uuid4().hex}"
    job = Job(
        title=title.strip(),
        normalized_title=normalize_title(title),
        description_text=notes or f"Manual application: {title} at {company}",
        description_html="",
        content_hash=content_hash,
        simhash=0,
        canonical_url=url or f"https://manual.local/{content_hash}",
        apply_url=url or f"https://manual.local/{content_hash}",
        status="open",
        meta={"company_name": company.strip(), "manual": True},
    )
    ctx.session.add(job)
    await ctx.session.flush()

    status = "submitted" if mark_submitted else "ready"
    now = datetime.now(UTC)
    app = Application(
        workspace_id=ctx.workspace_id,
        track_id=track_id,
        job_id=job.id,
        profile_id=track.profile_id,
        status=status,
        method=method,
        notes=notes,
        company_name=company.strip(),
        job_title=title.strip(),
        apply_url=url,
        tailored=False,
        submitted_at=now if mark_submitted else None,
        reminder_days=7,
        reminder_at=(now + timedelta(days=7)) if mark_submitted else None,
        follow_up_draft=draft_follow_up(company=company, title=title) if mark_submitted else "",
    )
    ctx.session.add(app)
    await ctx.session.flush()
    if mark_submitted and app.reminder_at:
        ctx.session.add(
            ApplicationReminder(
                workspace_id=ctx.workspace_id,
                application_id=app.id,
                kind="follow_up",
                due_at=app.reminder_at,
                draft=app.follow_up_draft,
            )
        )
    await _add_event(ctx, app, type="created", payload={"manual": True})
    if mark_submitted:
        await _add_event(ctx, app, type="submitted", payload={"method": method})
    await audit.record(
        ctx,
        action="application.created_manual",
        target_type="application",
        target_id=str(app.id),
        after={"company": company, "title": title},
    )
    await ctx.session.flush()
    return await get_application_detail(ctx, app.id)


async def suggest_ghosted(ctx: WorkspaceContext, *, days: int = 14) -> list[dict[str, Any]]:
    cutoff = datetime.now(UTC) - timedelta(days=days)
    rows = (
        (
            await ctx.session.execute(
                select(Application).where(
                    Application.workspace_id == ctx.workspace_id,
                    Application.status == "submitted",
                    Application.submitted_at.is_not(None),
                    Application.submitted_at <= cutoff,
                    Application.ghosted_suggested_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    out = []
    for app in rows:
        app.ghosted_suggested_at = datetime.now(UTC)
        out.append({"id": app.id, "job_title": app.job_title, "company_name": app.company_name})
    await ctx.session.flush()
    return out


async def export_applications(
    ctx: WorkspaceContext, *, fmt: str = "json"
) -> tuple[str, bytes, str]:
    data = await list_applications(ctx, limit=200, offset=0)
    items = data["items"]
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.DictWriter(
            buf,
            fieldnames=[
                "id",
                "status",
                "method",
                "company_name",
                "job_title",
                "apply_url",
                "submitted_at",
                "tailored",
                "lens_grade",
                "notes",
            ],
        )
        w.writeheader()
        for it in items:
            w.writerow(
                {
                    "id": str(it["id"]),
                    "status": it["status"],
                    "method": it["method"],
                    "company_name": it["company_name"],
                    "job_title": it["job_title"],
                    "apply_url": it["apply_url"],
                    "submitted_at": it["submitted_at"].isoformat() if it["submitted_at"] else "",
                    "tailored": it["tailored"],
                    "lens_grade": it["lens_grade"],
                    "notes": it["notes"],
                }
            )
        return "applications.csv", buf.getvalue().encode(), "text/csv"
    body = json.dumps(items, default=str, ensure_ascii=False, indent=2).encode()
    return "applications.json", body, "application/json"


async def list_saved_views(ctx: WorkspaceContext) -> list[dict[str, Any]]:
    rows = (
        (
            await ctx.session.execute(
                select(ApplicationSavedView).where(
                    ApplicationSavedView.workspace_id == ctx.workspace_id,
                    ApplicationSavedView.user_id == ctx.user_id,
                )
            )
        )
        .scalars()
        .all()
    )
    return [
        {"id": r.id, "name": r.name, "filters": r.filters or {}, "created_at": r.created_at}
        for r in rows
    ]


async def save_view(ctx: WorkspaceContext, *, name: str, filters: dict[str, Any]) -> dict[str, Any]:
    row = ApplicationSavedView(
        workspace_id=ctx.workspace_id,
        user_id=ctx.user_id,
        name=name.strip()[:120],
        filters=filters,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="application.saved_view",
        target_type="application_saved_view",
        target_id=str(row.id),
        after={"name": row.name},
    )
    return {"id": row.id, "name": row.name, "filters": row.filters, "created_at": row.created_at}
