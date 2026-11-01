"""Interview prep service."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.applications.models import Application
from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.interview import models as m
from app.interview.build import build_prep
from app.interview.schemas import InterviewPrepRead
from app.jobs.models import Job
from app.profiles.models import Bullet, Experience, Skill


async def _app(ctx: WorkspaceContext, application_id: uuid.UUID) -> Application:
    app = await ctx.session.get(Application, application_id)
    if app is None or app.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Application not found", 404)
    return app


async def get_prep(ctx: WorkspaceContext, application_id: uuid.UUID) -> InterviewPrepRead | None:
    await _app(ctx, application_id)
    row = (
        await ctx.session.execute(
            select(m.InterviewPrep).where(
                m.InterviewPrep.workspace_id == ctx.workspace_id,
                m.InterviewPrep.application_id == application_id,
            )
        )
    ).scalar_one_or_none()
    return InterviewPrepRead.model_validate(row) if row else None


async def generate_prep(ctx: WorkspaceContext, application_id: uuid.UUID) -> InterviewPrepRead:
    app = await _app(ctx, application_id)
    job = await ctx.session.get(Job, app.job_id)
    desc = (job.description_text if job else "") or ""

    skills = [
        s.name
        for s in (
            await ctx.session.execute(
                select(Skill).where(Skill.profile_id == app.profile_id, Skill.do_not_use.is_(False))
            )
        ).scalars()
        if s.name
    ]
    exps = list(
        (
            await ctx.session.execute(
                select(Experience)
                .where(
                    Experience.profile_id == app.profile_id,
                    Experience.do_not_use.is_(False),
                )
                .order_by(Experience.sort_order, Experience.start_date.desc().nullslast())
            )
        ).scalars()
    )
    bullets = list(
        (
            await ctx.session.execute(
                select(Bullet).where(
                    Bullet.profile_id == app.profile_id, Bullet.do_not_use.is_(False)
                )
            )
        ).scalars()
    )
    exp_dicts: list[dict[str, Any]] = [
        {
            "id": str(e.id),
            "company": e.company,
            "title": e.title,
            "description": e.description or "",
        }
        for e in exps
    ]
    bullet_dicts = [
        {
            "experience_id": str(b.experience_id) if b.experience_id else None,
            "text": b.text or "",
            "evidence_strength": b.evidence_strength,
        }
        for b in bullets
    ]

    payload = build_prep(
        company=app.company_name,
        title=app.job_title,
        job_description=desc,
        skills=skills,
        experiences=exp_dicts,
        bullets=bullet_dicts,
    )

    existing = (
        await ctx.session.execute(
            select(m.InterviewPrep).where(
                m.InterviewPrep.workspace_id == ctx.workspace_id,
                m.InterviewPrep.application_id == application_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.company_brief = payload["company_brief"]
        existing.likely_questions = payload["likely_questions"]
        existing.star_stories = payload["star_stories"]
        existing.checklist = payload["checklist"]
        existing.citations = payload["citations"]
        row = existing
    else:
        row = m.InterviewPrep(
            workspace_id=ctx.workspace_id,
            application_id=application_id,
            **payload,
        )
        ctx.session.add(row)

    await audit.record(
        ctx,
        action="interview.prep_generated",
        target_type="application",
        target_id=str(application_id),
    )
    await ctx.session.flush()
    return InterviewPrepRead.model_validate(row)
