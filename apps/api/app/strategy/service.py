"""Strategy service: Be Found + caps + salary + follow-ups."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.applications.follow_up import draft_follow_up
from app.applications.models import Application
from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.jobs.models import Job
from app.profiles.models import CandidateProfile, Experience, Skill
from app.strategy import caps as caps_mod
from app.strategy import consistency as cons_mod
from app.strategy import freshness as fresh_mod
from app.strategy import linkedin as li_mod
from app.strategy import salary as sal_mod
from app.strategy.schemas import (
    CapCheckRead,
    ConsistencyReport,
    FollowUpDraftsRead,
    FreshnessRead,
    LinkedInOptimizeRead,
    SalaryAdviceRead,
    StrategyPrefRead,
)
from app.tracks.models import Track, TrackCriteria
from app.workspaces.models import Workspace


async def _track(ctx: WorkspaceContext, track_id: uuid.UUID) -> Track:
    track = await ctx.session.get(Track, track_id)
    if track is None or track.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Track not found", 404)
    return track


async def _profile_bundle(
    ctx: WorkspaceContext, profile_id: uuid.UUID
) -> tuple[CandidateProfile, list[dict[str, Any]], list[str]]:
    profile = await ctx.session.get(CandidateProfile, profile_id)
    if profile is None or profile.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Profile not found", 404)
    exps = list(
        (
            await ctx.session.execute(
                select(Experience)
                .where(
                    Experience.profile_id == profile_id,
                    Experience.do_not_use.is_(False),
                )
                .order_by(Experience.sort_order, Experience.start_date.desc().nullslast())
            )
        ).scalars()
    )
    skills = list(
        (
            await ctx.session.execute(
                select(Skill).where(Skill.profile_id == profile_id, Skill.do_not_use.is_(False))
            )
        ).scalars()
    )
    exp_dicts = [
        {
            "company": e.company,
            "title": e.title,
            "description": e.description or "",
            "start_date": e.start_date.isoformat() if e.start_date else None,
            "end_date": e.end_date.isoformat() if e.end_date else None,
        }
        for e in exps
    ]
    skill_names = [s.name for s in skills if s.name]
    return profile, exp_dicts, skill_names


async def optimize_linkedin(ctx: WorkspaceContext, track_id: uuid.UUID) -> LinkedInOptimizeRead:
    track = await _track(ctx, track_id)
    criteria = (
        await ctx.session.execute(select(TrackCriteria).where(TrackCriteria.track_id == track_id))
    ).scalar_one_or_none()
    structured = (criteria.structured if criteria else {}) or {}
    profile, exps, skills = await _profile_bundle(ctx, track.profile_id)
    result = li_mod.build_suggestions(
        track_id=track.id,
        track_name=track.name,
        structured=structured,
        display_name=profile.display_name,
        headline=profile.headline,
        summary=profile.summary,
        location=profile.location,
        experiences=exps,
        skills=skills,
    )
    await audit.record(
        ctx,
        action="strategy.linkedin_optimize",
        target_type="track",
        target_id=str(track_id),
    )
    return result


async def consistency_report(
    ctx: WorkspaceContext, *, linkedin_text: str, track_id: uuid.UUID | None
) -> ConsistencyReport:
    if track_id:
        track = await _track(ctx, track_id)
        profile_id = track.profile_id
    else:
        profile = (
            await ctx.session.execute(
                select(CandidateProfile)
                .where(
                    CandidateProfile.workspace_id == ctx.workspace_id,
                    CandidateProfile.is_default.is_(True),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if profile is None:
            profile = (
                await ctx.session.execute(
                    select(CandidateProfile)
                    .where(CandidateProfile.workspace_id == ctx.workspace_id)
                    .limit(1)
                )
            ).scalar_one_or_none()
        if profile is None:
            raise AppError("not_found", "Profile not found", 404)
        profile_id = profile.id
    profile, exps, skills = await _profile_bundle(ctx, profile_id)
    report = cons_mod.check_consistency(
        linkedin_text=linkedin_text,
        experiences=exps,
        skills=skills,
        display_name=profile.display_name,
        headline=profile.headline,
    )
    await audit.record(
        ctx,
        action="strategy.consistency_check",
        target_type="profile",
        target_id=str(profile_id),
        after={"score": report.score, "issues": len(report.issues)},
    )
    return report


async def get_prefs(ctx: WorkspaceContext) -> StrategyPrefRead:
    ws = await ctx.session.get(Workspace, ctx.workspace_id)
    settings = (ws.settings if ws and hasattr(ws, "settings") else None) or {}
    if not isinstance(settings, dict):
        settings = {}
    strat = settings.get("strategy") if isinstance(settings.get("strategy"), dict) else {}
    cap, window = caps_mod.prefs_from_settings(strat)
    return StrategyPrefRead(company_cap=cap, company_cap_window_days=window)


async def update_prefs(
    ctx: WorkspaceContext, *, company_cap: int, window_days: int
) -> StrategyPrefRead:
    ws = await ctx.session.get(Workspace, ctx.workspace_id)
    if ws is None:
        raise AppError("not_found", "Workspace not found", 404)
    settings = dict(ws.settings or {}) if hasattr(ws, "settings") else {}
    strat = dict(settings.get("strategy") or {})
    strat["company_cap"] = company_cap
    strat["company_cap_window_days"] = window_days
    settings["strategy"] = strat
    if hasattr(ws, "settings"):
        ws.settings = settings
    await audit.record(
        ctx,
        action="strategy.prefs_updated",
        target_type="workspace",
        target_id=str(ctx.workspace_id),
        after=strat,
    )
    return StrategyPrefRead(company_cap=company_cap, company_cap_window_days=window_days)


async def company_cap_for_application(
    ctx: WorkspaceContext, application_id: uuid.UUID
) -> CapCheckRead:
    app = await ctx.session.get(Application, application_id)
    if app is None or app.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Application not found", 404)
    prefs = await get_prefs(ctx)
    return await caps_mod.check_company_cap(
        ctx,
        company_name=app.company_name,
        company_cap=prefs.company_cap,
        window_days=prefs.company_cap_window_days,
        exclude_application_id=app.id,
    )


async def job_freshness(ctx: WorkspaceContext, job_id: uuid.UUID) -> FreshnessRead:
    job = await ctx.session.get(Job, job_id)
    if job is None:
        raise AppError("not_found", "Job not found", 404)
    return fresh_mod.freshness_for(
        job_id=job.id, posted_at=job.posted_at, first_seen_at=job.first_seen_at
    )


async def salary_for_application(
    ctx: WorkspaceContext, application_id: uuid.UUID
) -> SalaryAdviceRead:
    app = await ctx.session.get(Application, application_id)
    if app is None or app.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Application not found", 404)
    job = await ctx.session.get(Job, app.job_id)
    profile = await ctx.session.get(CandidateProfile, app.profile_id)
    market = None
    if job and isinstance(job.meta, dict):
        market = job.meta.get("market_salary_p50") or job.meta.get("adzuna_p50")
        try:
            market = float(market) if market is not None else None
        except (TypeError, ValueError):
            market = None
    return sal_mod.advise_salary(
        posting_salary=job.salary if job else {},
        user_salary_prefs=profile.salary_prefs if profile else {},
        market_p50=market,
    )


async def follow_up_drafts(ctx: WorkspaceContext, application_id: uuid.UUID) -> FollowUpDraftsRead:
    app = await ctx.session.get(Application, application_id)
    if app is None or app.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Application not found", 404)
    profile = await ctx.session.get(CandidateProfile, app.profile_id)
    name = profile.display_name if profile else ""
    return FollowUpDraftsRead(
        day_7=draft_follow_up(company=app.company_name, title=app.job_title, user_name=name, day=7),
        day_14=draft_follow_up(
            company=app.company_name, title=app.job_title, user_name=name, day=14
        ),
    )
