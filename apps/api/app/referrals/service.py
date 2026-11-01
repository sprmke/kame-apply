"""Contacts import + company matches + outreach drafts (user sends)."""

from __future__ import annotations

import re
import uuid

from sqlalchemy import func, select

from app.applications.models import Application
from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.profiles.models import CandidateProfile
from app.referrals import models as m
from app.referrals.schemas import (
    ContactCreate,
    ContactImportResult,
    ContactRead,
    MatchRead,
    ReferralDraftRead,
)


def _norm_company(name: str) -> str:
    s = (name or "").casefold().strip()
    s = re.sub(r"\b(inc|llc|ltd|corp|co|gmbh|plc)\b\.?", "", s)
    return re.sub(r"[^a-z0-9]+", "", s)


def _contact_read(row: m.Contact) -> ContactRead:
    return ContactRead.model_validate(row)


async def import_contacts(ctx: WorkspaceContext, items: list[ContactCreate]) -> ContactImportResult:
    count = 0
    for item in items:
        row = m.Contact(
            workspace_id=ctx.workspace_id,
            name=item.name.strip(),
            email=(item.email or "").strip()[:320],
            company=(item.company or "").strip()[:200],
            title=(item.title or "").strip()[:200],
            linkedin_url=(item.linkedin_url or "").strip()[:500],
            source=(item.source or "csv")[:32],
        )
        ctx.session.add(row)
        count += 1
    await audit.record(
        ctx,
        action="contacts.imported",
        target_type="workspace",
        target_id=str(ctx.workspace_id),
        after={"count": count},
    )
    await ctx.session.flush()
    return ContactImportResult(imported=count)


async def list_contacts(ctx: WorkspaceContext, *, q: str | None = None) -> list[ContactRead]:
    query = (
        select(m.Contact)
        .where(m.Contact.workspace_id == ctx.workspace_id)
        .order_by(m.Contact.created_at.desc())
        .limit(500)
    )
    if q:
        like = f"%{q.strip()}%"
        query = query.where(
            (m.Contact.name.ilike(like))
            | (m.Contact.company.ilike(like))
            | (m.Contact.email.ilike(like))
        )
    rows = list((await ctx.session.execute(query)).scalars())
    return [_contact_read(r) for r in rows]


async def matches_for_application(
    ctx: WorkspaceContext, application_id: uuid.UUID
) -> list[MatchRead]:
    app = await ctx.session.get(Application, application_id)
    if app is None or app.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Application not found", 404)
    target = _norm_company(app.company_name)
    if not target:
        return []
    rows = list(
        (
            await ctx.session.execute(
                select(m.Contact).where(m.Contact.workspace_id == ctx.workspace_id)
            )
        ).scalars()
    )
    out: list[MatchRead] = []
    for c in rows:
        cn = _norm_company(c.company)
        if not cn:
            continue
        if cn == target or cn in target or target in cn:
            score = 1.0 if cn == target else 0.7
            out.append(
                MatchRead(
                    contact=_contact_read(c),
                    score=score,
                    reason=f"Company match: {c.company}",
                )
            )
    out.sort(key=lambda x: -x.score)
    return out[:20]


def _draft_text(*, name: str, company: str, title: str, display_name: str) -> str:
    who = display_name or "I"
    role = title or "a role"
    return (
        f"Hi {name.split()[0] if name else 'there'},\n\n"
        f"I noticed you work at {company or 'your company'}. "
        f"{who} recently applied for {role} and would value any referral "
        f"or pointer you are comfortable sharing.\n\n"
        f"Happy to send a short blurb and resume. Thanks either way.\n"
    )


async def create_draft(
    ctx: WorkspaceContext, application_id: uuid.UUID, contact_id: uuid.UUID
) -> ReferralDraftRead:
    app = await ctx.session.get(Application, application_id)
    if app is None or app.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Application not found", 404)
    contact = await ctx.session.get(m.Contact, contact_id)
    if contact is None or contact.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Contact not found", 404)

    profile = await ctx.session.get(CandidateProfile, app.profile_id)
    display = (profile.display_name if profile else "") or ""
    text = _draft_text(
        name=contact.name,
        company=app.company_name or contact.company,
        title=app.job_title,
        display_name=display,
    )
    row = m.ReferralDraft(
        workspace_id=ctx.workspace_id,
        application_id=application_id,
        contact_id=contact.id,
        draft=text,
    )
    ctx.session.add(row)
    await audit.record(
        ctx,
        action="referral.draft_created",
        target_type="application",
        target_id=str(application_id),
        after={"contact_id": str(contact_id)},
    )
    await ctx.session.flush()
    return ReferralDraftRead(
        id=row.id,
        application_id=row.application_id,
        contact_id=row.contact_id,
        draft=row.draft,
        created_at=row.created_at,
        contact_name=contact.name,
    )


async def list_drafts(ctx: WorkspaceContext, application_id: uuid.UUID) -> list[ReferralDraftRead]:
    app = await ctx.session.get(Application, application_id)
    if app is None or app.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Application not found", 404)
    rows = (
        await ctx.session.execute(
            select(m.ReferralDraft, m.Contact)
            .outerjoin(m.Contact, m.Contact.id == m.ReferralDraft.contact_id)
            .where(
                m.ReferralDraft.workspace_id == ctx.workspace_id,
                m.ReferralDraft.application_id == application_id,
            )
            .order_by(m.ReferralDraft.created_at.desc())
        )
    ).all()
    out: list[ReferralDraftRead] = []
    for draft, contact in rows:
        out.append(
            ReferralDraftRead(
                id=draft.id,
                application_id=draft.application_id,
                contact_id=draft.contact_id,
                draft=draft.draft,
                created_at=draft.created_at,
                contact_name=contact.name if contact else "",
            )
        )
    return out


async def coach_overview(ctx: WorkspaceContext) -> list[dict]:
    """Multi-profile summary for coach/agency UI."""
    from app.profiles.models import CandidateProfile

    profiles = list(
        (
            await ctx.session.execute(
                select(CandidateProfile)
                .where(CandidateProfile.workspace_id == ctx.workspace_id)
                .order_by(CandidateProfile.is_default.desc(), CandidateProfile.created_at)
            )
        ).scalars()
    )
    out = []
    for p in profiles:
        app_count = (
            await ctx.session.execute(
                select(func.count())
                .select_from(Application)
                .where(
                    Application.workspace_id == ctx.workspace_id,
                    Application.profile_id == p.id,
                )
            )
        ).scalar_one()
        out.append(
            {
                "id": str(p.id),
                "display_name": p.display_name,
                "headline": p.headline,
                "is_default": p.is_default,
                "application_count": int(app_count or 0),
            }
        )
    return out
