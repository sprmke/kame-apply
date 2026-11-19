"""Apply a reviewed setup bundle through the existing services, in one transaction.

Nothing here trusts a raw bundle value: every write re-validates through the target registry and
then the owning service's create/update schema. Answers, facts, searches, schedules, voice, studio,
and account writes each emit their own audit row; setup adds one `setup.applied` summary.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select

from app.audit import service as audit
from app.auth.models import User
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.onboarding import schemas as s
from app.onboarding.targets import TargetError, answer_target_with_country, validate_target
from app.profiles import models as profile_models
from app.profiles import schemas as profile_schemas
from app.profiles.answers import create_answer, list_answers, update_answer
from app.profiles.models import VoiceProfile
from app.profiles.service import create_item, get_profile, update_item, update_profile
from app.profiles.voice import apply_preset
from app.resumes.service import create_base
from app.tracks.criteria import SalaryFilter, SkillSets
from app.tracks.models import Track
from app.tracks.schemas import TrackCreate
from app.tracks.service import create_track
from app.tracks.summary import summarize

HEADER_TARGETS: dict[str, str] = {
    "profile.display_name": "display_name",
    "profile.headline": "headline",
    "profile.summary": "summary",
    "profile.location": "location",
    "profile.timezone": "timezone",
    "profile.language": "language",
    "profile.links": "links",
    "profile.salary_prefs": "salary_prefs",
    "profile.work_authorization": "work_authorization",
}

FACT_TARGETS: dict[str, tuple[str, type, type]] = {
    "profile.experience": (
        "experiences",
        profile_schemas.ExperienceIn,
        profile_schemas.ExperiencePatch,
    ),
    "profile.project": ("projects", profile_schemas.ProjectIn, profile_schemas.ProjectPatch),
    "profile.education": ("education", profile_schemas.EducationIn, profile_schemas.EducationPatch),
    "profile.certification": (
        "certifications",
        profile_schemas.CertificationIn,
        profile_schemas.CertificationPatch,
    ),
    "profile.spoken_language": (
        "languages",
        profile_schemas.LanguageIn,
        profile_schemas.LanguagePatch,
    ),
    "profile.skill": ("skills", profile_schemas.SkillIn, profile_schemas.SkillPatch),
}

ANSWER_PREFIX = "answers."
SEARCH_PREFIX = "searches."
REVERT_WINDOW = timedelta(days=7)


@dataclass
class Resolved:
    item: s.SetupItem
    action: str
    value: Any


@dataclass
class ApplyOutcome:
    draft_id: uuid.UUID
    profile_id: uuid.UUID
    applied_at: datetime
    created: dict[str, list[uuid.UUID]]
    updated: dict[str, list[uuid.UUID]]
    counts: dict[str, int]
    links: dict[str, str]
    before: dict[str, Any]
    written: dict[str, Any]
    search_ids: list[uuid.UUID]


# ---- decision resolution ---------------------------------------------------------------------


def _decision_value(item: s.SetupItem, decision: s.ItemDecision | None) -> Any:
    if decision is not None and decision.edited:
        return decision.value
    return item.value


def _answer_payload(value: Any) -> Any:
    if isinstance(value, str):
        return {"answer": value, "approved": True}
    if isinstance(value, dict) and value.get("approved") is False:
        return {**value, "approved": True}
    return value


def resolve(
    bundle: s.SetupBundle,
    decisions: s.SetupDecisions,
) -> tuple[list[Resolved], dict[str, str]]:
    """Validate every selected value. Returns the writes and per-item errors."""
    writes: list[Resolved] = []
    errors: dict[str, str] = {}
    for item in bundle.items:
        decision = decisions.items.get(item.id)
        action = decision.action if decision is not None and decision.action else item.action
        if item.blocked not in {"ok"} or action in {"skip", "keep_current"}:
            continue
        value = _decision_value(item, decision)
        if item.needs_you:
            if value in (None, "", [], {}):
                continue
            value = _answer_payload(value)
        if value in (None, "", [], {}):
            errors[item.id] = "Add a value or skip this row."
            continue
        target = answer_target_with_country(item.target, decision.country if decision else None)
        try:
            validated = validate_target(target, value)
        except TargetError as exc:
            errors[item.id] = str(exc)
            continue
        resolved = item if target == item.target else item.model_copy(update={"target": target})
        writes.append(Resolved(item=resolved, action=action, value=validated))
    return writes, errors


def needs_you_count(bundle: s.SetupBundle, decisions: s.SetupDecisions) -> int:
    """How many needs-you rows the user left empty; they become a Needs you item."""
    count = 0
    for item in bundle.items:
        if not item.needs_you:
            continue
        decision = decisions.items.get(item.id)
        value = _decision_value(item, decision)
        if value in (None, "", [], {}):
            count += 1
    return count


def selected_searches(bundle: s.SetupBundle, decisions: s.SetupDecisions) -> list[s.SearchProposal]:
    out: list[s.SearchProposal] = []
    for proposal in bundle.searches:
        key = f"{SEARCH_PREFIX}{proposal.variant}"
        decision = decisions.items.get(key)
        action = (
            decision.action
            if decision is not None and decision.action
            else ("add" if proposal.default_on and proposal.blocked == "ok" else "skip")
        )
        if action in {"skip", "keep_current"}:
            continue
        if proposal.blocked != "ok":
            continue
        override = decisions.searches.get(proposal.variant)
        if override is not None:
            out.append(
                override.model_copy(
                    update={
                        "blocked": proposal.blocked,
                        "default_on": proposal.default_on,
                        "duplicate_of": proposal.duplicate_of,
                        "variant": proposal.variant,
                    }
                )
            )
            continue
        out.append(proposal)
    return out


# ---- current-value annotations (update mode) -------------------------------------------------


def _fact_key(target: str, value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    if target == "profile.experience":
        return f"{value.get('company', '')}|{value.get('title', '')}".casefold()
    if target == "profile.project":
        return str(value.get("name") or "").casefold()
    if target == "profile.education":
        return str(value.get("institution") or "").casefold()
    if target == "profile.certification":
        return str(value.get("name") or "").casefold()
    if target == "profile.spoken_language":
        return str(value.get("name") or "").casefold()
    if target == "profile.skill":
        from app.taxonomy.aliases import skill_key

        return skill_key(str(value.get("name") or ""))
    return ""


async def annotate_current(
    ctx: WorkspaceContext, draft: Any, bundle: s.SetupBundle
) -> s.SetupBundle:
    """Update mode: show what exists, never overwrite it by default."""
    profile = await get_profile(ctx, draft.profile_id)
    items = [item.model_copy() for item in bundle.items]

    for item in items:
        if item.group == "profile" and item.target in HEADER_TARGETS:
            current = getattr(profile, HEADER_TARGETS[item.target], None)
            if current in (None, "", [], {}):
                continue
            item.current = current
            if current == item.value:
                item.action = "keep_current"
                item.default_on = False
            else:
                item.action = "keep_current"
                item.default_on = False

    existing: dict[str, uuid.UUID] = {}
    for target, (section, _create, _patch) in FACT_TARGETS.items():
        rows = await _section_rows(ctx, draft.profile_id, section)
        for row in rows:
            key = _fact_key(
                target,
                {
                    "company": getattr(row, "company", ""),
                    "title": getattr(row, "title", ""),
                    "name": getattr(row, "name", ""),
                    "institution": getattr(row, "institution", ""),
                },
            )
            if key:
                existing[f"{target}|{key}"] = row.id
    for item in items:
        if item.target not in FACT_TARGETS or not isinstance(item.value, dict):
            continue
        key = _fact_key(item.target, item.value)
        match = existing.get(f"{item.target}|{key}")
        if match is not None:
            item.current = {"id": str(match)}
            item.current_id = match
            item.action = "keep_current"
            item.blocked = "duplicate"
            item.default_on = False

    answers = await list_answers(ctx, draft.profile_id)
    by_slot = {(row.key, row.country): row for row in answers}
    for item in items:
        if not item.target.startswith(ANSWER_PREFIX):
            continue
        _key, country = _answer_slot(item.target)
        row = by_slot.get((_key, country))
        if row is None:
            continue
        proposed = item.value if isinstance(item.value, dict) else {}
        same = row.answer == str(proposed.get("answer") or "")
        item.current = row.answer
        item.current_id = row.id
        if same or row.approved:
            item.action = "keep_current"
            item.default_on = False
        else:
            item.action = "replace"

    voice = (
        await ctx.session.execute(
            select(VoiceProfile).where(VoiceProfile.profile_id == draft.profile_id)
        )
    ).scalar_one_or_none()
    if voice is not None and (voice.samples or (voice.style or {}).get("preset")):
        for item in items:
            if item.target == "writing.preset":
                item.action = "keep_current"
                item.default_on = False

    from app.resumes.models import ResumeVersion

    has_base = (
        await ctx.session.execute(
            select(func.count())
            .select_from(ResumeVersion)
            .where(
                ResumeVersion.profile_id == draft.profile_id,
                ResumeVersion.kind == "base",
            )
        )
    ).scalar_one()
    if has_base:
        for item in items:
            if item.target == "studio.base_resume":
                item.action = "keep_current"
                item.default_on = False

    from app.workspaces.limits import get_limits

    limits = await get_limits(ctx.session, ctx.workspace_id)
    active = (
        await ctx.session.execute(
            select(func.count())
            .select_from(Track)
            .where(
                Track.workspace_id == ctx.workspace_id,
                Track.status == "active",
            )
        )
    ).scalar_one()
    room = max(0, int(limits["max_tracks"]) - int(active))
    proposals = [proposal.model_copy() for proposal in bundle.searches]
    for index, proposal in enumerate(proposals):
        if proposal.duplicate_of is not None:
            proposal.blocked = "duplicate"
            proposal.default_on = False
        if index >= room:
            proposal.blocked = "limit"
            proposal.default_on = False
    return bundle.model_copy(update={"items": items, "searches": proposals})


async def _section_rows(ctx: WorkspaceContext, profile_id: uuid.UUID, section: str) -> list[Any]:
    model = {
        "experiences": profile_models.Experience,
        "projects": profile_models.Project,
        "education": profile_models.Education,
        "certifications": profile_models.Certification,
        "languages": profile_models.Language,
        "skills": profile_models.Skill,
    }[section]
    return list(
        (await ctx.session.execute(select(model).where(model.profile_id == profile_id))).scalars()
    )


def _answer_slot(target: str) -> tuple[str, str | None]:
    parts = target.split(".")
    key = parts[1] if len(parts) > 1 else ""
    country = parts[2].upper() if len(parts) > 2 else None
    return key, country


# ---- apply -----------------------------------------------------------------------------------


async def _write_profile_header(
    ctx: WorkspaceContext,
    profile: Any,
    writes: list[Resolved],
    created: dict[str, list[uuid.UUID]],
    before: dict[str, Any],
) -> None:
    fields: dict[str, Any] = {}
    for write in writes:
        if write.item.target in HEADER_TARGETS:
            fields[HEADER_TARGETS[write.item.target]] = write.value
    if not fields:
        return
    before["profile"] = {key: getattr(profile, key) for key in fields}
    await update_profile(ctx, profile.id, profile_schemas.ProfileUpdate(**fields))
    created.setdefault("profile", []).append(profile.id)


async def _write_facts(
    ctx: WorkspaceContext, profile_id: uuid.UUID, writes: list[Resolved]
) -> tuple[dict[str, list[uuid.UUID]], dict[str, list[uuid.UUID]]]:
    created: dict[str, list[uuid.UUID]] = {}
    updated: dict[str, list[uuid.UUID]] = {}
    for write in writes:
        spec = FACT_TARGETS.get(write.item.target)
        if spec is None:
            continue
        section, create_schema, patch_schema = spec
        if not isinstance(write.value, dict):
            continue
        if write.action == "replace" and write.item.current_id is not None:
            row = await update_item(
                ctx,
                profile_id,
                section,
                write.item.current_id,
                patch_schema(**write.value),
            )
            updated.setdefault(section, []).append(row.id)  # type: ignore[attr-defined]
            continue
        row = await create_item(ctx, profile_id, section, create_schema(**write.value))
        created.setdefault(section, []).append(row.id)  # type: ignore[attr-defined]
    return created, updated


async def _write_answers(
    ctx: WorkspaceContext, profile_id: uuid.UUID, writes: list[Resolved]
) -> tuple[list[uuid.UUID], list[uuid.UUID], dict[str, Any], dict[str, Any]]:
    created: list[uuid.UUID] = []
    updated: list[uuid.UUID] = []
    before: dict[str, Any] = {}
    written: dict[str, Any] = {}
    rows = await list_answers(ctx, profile_id)
    by_slot = {(row.key, row.country): row for row in rows}
    for write in writes:
        if not write.item.target.startswith(ANSWER_PREFIX):
            continue
        key, country = _answer_slot(write.item.target)
        payload = write.value if isinstance(write.value, dict) else {}
        row = by_slot.get((key, country))
        if row is not None:
            before[str(row.id)] = {"answer": row.answer, "approved": row.approved}
            await update_answer(
                ctx,
                profile_id,
                row.id,
                profile_schemas.AnswerUpdate(
                    answer=str(payload.get("answer") or ""),
                    approved=bool(payload.get("approved", False)),
                ),
            )
            updated.append(row.id)
            written[str(row.id)] = {
                "answer": str(payload.get("answer") or ""),
                "approved": bool(payload.get("approved", False)),
            }
            continue
        row = await create_answer(
            ctx,
            profile_id,
            profile_schemas.AnswerCreate(
                key=key,
                country=country,
                answer=str(payload.get("answer") or ""),
                approved=bool(payload.get("approved", False)),
            ),
        )
        created.append(row.id)
        written[str(row.id)] = {
            "answer": str(payload.get("answer") or ""),
            "approved": bool(payload.get("approved", False)),
        }
        by_slot[(key, country)] = row
    return created, updated, before, written


async def apply_bundle(
    ctx: WorkspaceContext,
    draft: Any,
    bundle: s.SetupBundle,
    decisions: s.SetupDecisions,
) -> ApplyOutcome:
    profile = await get_profile(ctx, draft.profile_id)
    writes, errors = resolve(bundle, decisions)
    if errors:
        raise AppError(
            "setup_invalid_items",
            "Some values need a fix before saving",
            422,
            {"items": errors},
        )
    created: dict[str, list[uuid.UUID]] = {}
    updated: dict[str, list[uuid.UUID]] = {}
    before: dict[str, Any] = {}
    written: dict[str, Any] = {}

    lowest = (
        decisions.lowest_pay
        if decisions.lowest_pay_set
        else (bundle.lowest_pay if decisions.lowest_pay is None else decisions.lowest_pay)
    )
    if lowest is not None:
        writes = [
            write
            for write in writes
            if write.item.target not in {"profile.salary_prefs", "answers.salary_expectation"}
        ]

    await _write_profile_header(ctx, profile, writes, created, before)
    if "profile" in before:
        written["profile"] = {field: getattr(profile, field) for field in before["profile"]}
    fact_created, fact_updated = await _write_facts(ctx, profile.id, writes)
    for key, ids in fact_created.items():
        created.setdefault(key, []).extend(ids)
    for key, ids in fact_updated.items():
        updated.setdefault(key, []).extend(ids)

    answer_created, answer_updated, answer_before, answer_written = await _write_answers(
        ctx, profile.id, writes
    )
    if answer_created:
        created["answers"] = answer_created
    if answer_updated:
        updated["answers"] = answer_updated
    if answer_before:
        before["answers"] = answer_before
    if answer_written:
        written["answers"] = answer_written

    for write in writes:
        if write.item.target != "writing.preset":
            continue
        voice = (
            await ctx.session.execute(
                select(VoiceProfile).where(VoiceProfile.profile_id == profile.id)
            )
        ).scalar_one_or_none()
        if voice is not None and voice.samples:
            continue
        before["voice_preset"] = (voice.style or {}).get("preset") if voice else None
        await apply_preset(ctx, profile.id, profile_schemas.VoicePresetBody(preset=write.value))
        created.setdefault("voice", []).append(profile.id)

    proposals = selected_searches(bundle, decisions)
    if lowest is not None:
        (
            salary_created,
            salary_updated,
            salary_before,
            salary_written,
            proposals,
        ) = await _apply_lowest_pay(ctx, profile, lowest, proposals)
        if salary_created:
            created.setdefault("answers", []).extend(salary_created)
            created.setdefault("profile", []).append(profile.id)
        if salary_updated:
            updated.setdefault("answers", []).extend(salary_updated)
            updated.setdefault("profile", []).append(profile.id)
        if salary_before:
            before.setdefault("answers", {}).update(salary_before)
            before["salary_prefs"] = profile.salary_prefs
        if salary_written:
            written.setdefault("answers", {}).update(salary_written)

    own_skills = [row.name for row in await _section_rows(ctx, profile.id, "skills")]
    search_ids: list[uuid.UUID] = []
    for proposal in proposals:
        criteria = _guard_criteria(proposal, own_skills)
        result = await create_track(
            ctx,
            TrackCreate(
                profile_id=profile.id,
                name=proposal.name,
                nl_text=proposal.nl_text,
                criteria=criteria,
                autonomy=proposal.autonomy,
                suggest=False,
            ),
        )
        track = result["track"]
        search_ids.append(track.id)
        schedule = await _create_schedule(ctx, track.id, proposal.schedule)
        created.setdefault("searches", []).append(track.id)
        created.setdefault("schedules", []).append(schedule["id"])

    studio = next(
        (
            write
            for write in writes
            if write.item.target == "studio.base_resume" and isinstance(write.value, dict)
        ),
        None,
    )
    if studio is not None:
        resume = await create_base(
            ctx,
            profile_id=profile.id,
            track_id=search_ids[0] if search_ids else None,
            label=str(studio.value.get("label") or "Base resume"),
            template=str(studio.value.get("template") or "classic"),
            page_size=str(studio.value.get("page_size") or "a4"),
        )
        created.setdefault("resumes", []).append(resume["id"])  # type: ignore[index]

    account = {write.item.target: write.value for write in writes if write.item.group == "account"}
    if account:
        user = await ctx.session.get(User, ctx.user_id)
        if user is not None:
            before["account"] = {"name": user.name, "timezone": user.timezone}
            if account.get("account.name"):
                user.name = str(account["account.name"])
            if account.get("account.timezone"):
                user.timezone = str(account["account.timezone"])
            written["account"] = {"name": user.name, "timezone": user.timezone}
            await audit.record(
                ctx,
                action="user.updated",
                target_type="user",
                target_id=str(user.id),
                after={"fields": sorted(account)},
            )

    now = datetime.now(UTC)
    kept = 0
    for item in bundle.items:
        decision = decisions.items.get(item.id)
        action = decision.action if decision is not None and decision.action else item.action
        if action in {"add", "fill_blank", "replace"}:
            kept += 1
    skipped = len(bundle.items) - kept
    counts = {
        "kept": kept,
        "skipped": skipped,
        "created": sum(len(v) for v in created.values()),
        "needs_you": sum(1 for item in bundle.items if item.needs_you),
    }
    links = {
        "profile": "/profile",
        "answers": "/profile/answers",
        "searches": "/tracks",
        "studio": "/studio",
        "improve": f"/tracks/{search_ids[0]}/improve" if search_ids else "/tracks",
    }
    needs_you = 0
    for item in bundle.items:
        if not item.needs_you:
            continue
        decision = decisions.items.get(item.id)
        value = _decision_value(item, decision) if decision is not None else item.value
        if value in (None, "", [], {}):
            needs_you += 1
    return ApplyOutcome(
        draft_id=draft.id,
        profile_id=profile.id,
        applied_at=now,
        created=created,
        updated=updated,
        counts={**counts, "needs_you": needs_you},
        links=links,
        before=before,
        written=written,
        search_ids=search_ids,
    )


def _guard_criteria(proposal: s.SearchProposal, own_skills: list[str]) -> Any:
    """Keep the person's own skills as the only must-haves and leave the wide fields empty."""
    from app.taxonomy.aliases import same_skill

    must = [
        skill
        for skill in proposal.criteria.skills.must
        if any(same_skill(skill, own) for own in own_skills)
    ]
    criteria = proposal.criteria.model_copy(
        update={
            "skills": SkillSets(must=must, nice=list(proposal.criteria.skills.nice)),
            "languages": [],
            "education": None,
            "clearance": None,
        }
    )
    return criteria


async def _apply_lowest_pay(
    ctx: WorkspaceContext,
    profile: Any,
    lowest: s.SalaryInput,
    proposals: list[s.SearchProposal],
) -> tuple[
    list[uuid.UUID], list[uuid.UUID], dict[str, Any], dict[str, Any], list[s.SearchProposal]
]:
    """One input, three places: profile pay floor, salary answer, every selected search."""
    amount = float(lowest.amount)
    text = f"{lowest.currency} {amount:,.0f} per {lowest.period}"
    created: list[uuid.UUID] = []
    updated: list[uuid.UUID] = []
    before: dict[str, Any] = {}
    written: dict[str, Any] = {}

    await update_profile(
        ctx,
        profile.id,
        profile_schemas.ProfileUpdate(
            salary_prefs={
                "floor": amount,
                "currency": lowest.currency,
                "period": lowest.period,
            }
        ),
    )
    rows = await list_answers(ctx, profile.id)
    row = next(
        (item for item in rows if item.key == "salary_expectation" and item.country is None),
        None,
    )
    if row is not None:
        before[str(row.id)] = {"answer": row.answer, "approved": row.approved}
        await update_answer(
            ctx,
            profile.id,
            row.id,
            profile_schemas.AnswerUpdate(answer=text, approved=True),
        )
        updated.append(row.id)
        written[str(row.id)] = {"answer": text, "approved": True}
    else:
        row = await create_answer(
            ctx,
            profile.id,
            profile_schemas.AnswerCreate(key="salary_expectation", answer=text, approved=True),
        )
        created.append(row.id)
        written[str(row.id)] = {"answer": text, "approved": True}

    salary = SalaryFilter(min=amount, currency=lowest.currency, period=lowest.period)
    out: list[s.SearchProposal] = []
    for proposal in proposals:
        criteria = proposal.criteria.model_copy(update={"salary": salary})
        out.append(
            proposal.model_copy(update={"criteria": criteria, "summary": summarize(criteria)})
        )
    return created, updated, before, written, out


async def _create_schedule(ctx: WorkspaceContext, track_id: uuid.UUID, defaults: Any) -> Any:
    from app.schedules import service as schedule_service

    return await schedule_service.create_schedule(
        ctx,
        track_id,
        {
            "preset": defaults.preset,
            "timezone": defaults.timezone,
            "quiet_hours": dict(defaults.quiet_hours),
            "daily_cap": defaults.daily_cap,
        },
    )


# ---- revert ----------------------------------------------------------------------------------


async def revert_bundle(
    ctx: WorkspaceContext, draft: Any
) -> tuple[dict[str, int], list[dict[str, str]]]:
    """Undo what setup created, only where the value still equals what setup wrote."""
    result = dict(draft.result or {})
    applied_at = draft.applied_at
    if applied_at is None:
        raise AppError("setup_not_applied", "This setup was not applied", 409)
    if datetime.now(UTC) - applied_at > REVERT_WINDOW:
        raise AppError(
            "setup_revert_window_closed",
            "Undo is available for 7 days after setup.",
            409,
        )
    removed: dict[str, int] = {}
    kept: list[dict[str, str]] = []
    created = result.get("created") or {}
    before = result.get("before") or {}

    for track_id in created.get("searches") or []:
        track = await ctx.session.get(Track, uuid.UUID(str(track_id)))
        if track is None:
            continue
        from app.applications.models import Application

        apps = (
            await ctx.session.execute(
                select(func.count())
                .select_from(Application)
                .where(Application.track_id == track.id)
            )
        ).scalar_one()
        if apps:
            track.status = "archived"
            kept.append({"kind": "search", "id": str(track.id), "why": "has applications"})
        else:
            await ctx.session.delete(track)
            removed["searches"] = removed.get("searches", 0) + 1

    from app.profiles.models import AnswerBank
    from app.resumes.models import ResumeVersion

    written_answers = (result.get("written") or {}).get("answers") or {}
    for answer_id in created.get("answers") or []:
        row = await ctx.session.get(AnswerBank, uuid.UUID(str(answer_id)))
        if row is None:
            continue
        written = written_answers.get(str(row.id)) or {}
        if written and (
            row.answer != written.get("answer") or row.approved != written.get("approved")
        ):
            kept.append({"kind": "answer", "id": str(row.id), "why": "edited after setup"})
            continue
        await ctx.session.delete(row)
        removed["answers"] = removed.get("answers", 0) + 1

    for answer_id, old in (before.get("answers") or {}).items():
        row = await ctx.session.get(AnswerBank, uuid.UUID(str(answer_id)))
        if row is None:
            continue
        written = written_answers.get(str(row.id)) or {}
        if not written:
            continue
        if row.answer != written.get("answer") or row.approved != written.get("approved"):
            kept.append({"kind": "answer", "id": str(row.id), "why": "edited after setup"})
            continue
        row.answer = str(old.get("answer") or "")
        row.approved = bool(old.get("approved", False))
        removed["answers_restored"] = removed.get("answers_restored", 0) + 1

    fact_models = {
        "experiences": profile_models.Experience,
        "projects": profile_models.Project,
        "education": profile_models.Education,
        "certifications": profile_models.Certification,
        "languages": profile_models.Language,
        "skills": profile_models.Skill,
    }
    for section, model in fact_models.items():
        for row_id in created.get(section) or []:
            row = await ctx.session.get(model, uuid.UUID(str(row_id)))
            if row is None:
                continue
            if row.updated_at > applied_at + timedelta(seconds=1):
                kept.append({"kind": section, "id": str(row.id), "why": "edited after setup"})
                continue
            await ctx.session.delete(row)
            removed[section] = removed.get(section, 0) + 1

    for resume_id in created.get("resumes") or []:
        row = await ctx.session.get(ResumeVersion, uuid.UUID(str(resume_id)))
        if row is None:
            continue
        if row.updated_at > applied_at + timedelta(seconds=1):
            kept.append({"kind": "resume", "id": str(row.id), "why": "edited after setup"})
            continue
        await ctx.session.delete(row)
        removed["resumes"] = removed.get("resumes", 0) + 1

    profile = await get_profile(ctx, draft.profile_id)
    for field, old in (before.get("profile") or {}).items():
        if getattr(profile, field, None) == _written_value(result, field):
            setattr(profile, field, old)
            removed["profile_fields"] = removed.get("profile_fields", 0) + 1
        else:
            kept.append({"kind": "profile", "id": field, "why": "edited after setup"})

    if "voice_preset" in before:
        voice = (
            await ctx.session.execute(
                select(VoiceProfile).where(VoiceProfile.profile_id == profile.id)
            )
        ).scalar_one_or_none()
        if voice is not None and (voice.style or {}).get("preset") == result.get("voice_preset"):
            old = before.get("voice_preset")
            if old:
                await apply_preset(ctx, profile.id, profile_schemas.VoicePresetBody(preset=old))
                removed["voice"] = 1

    account_before = before.get("account") or {}
    if account_before:
        user = await ctx.session.get(User, ctx.user_id)
        if user is not None:
            if user.name == result.get("account_name"):
                user.name = account_before.get("name")
                removed["account"] = removed.get("account", 0) + 1

    await ctx.session.flush()
    return removed, kept


def _written_value(result: dict[str, Any], field: str) -> Any:
    return (result.get("written") or {}).get(field)
