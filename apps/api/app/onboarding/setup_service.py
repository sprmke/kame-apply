"""Setup draft lifecycle: create, read, cancel, retry, discard, and retention.

A draft is the only new write path. Applying it (S4) calls the existing profile, answer, track,
schedule, voice, resume, and account services.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified

from app.audit import service as audit
from app.core.errors import AppError
from app.core.rls import set_request_context
from app.core.security import WorkspaceContext
from app.onboarding import apply as apply_module
from app.onboarding import models as m
from app.onboarding import pipeline
from app.onboarding import schemas as s
from app.profiles import schemas as profile_schemas
from app.profiles.answers import list_answers
from app.profiles.documents import create_text_document, get_document
from app.profiles.service import (
    create_profile,
    get_profile,
    list_profiles,
    profile_has_facts,
)
from app.tracks.models import Track

OPEN_TTL_DAYS = 14
CONTENT_RETENTION_DAYS = 30
OPEN_STATUSES = ("queued", "running", "ready", "applying")
FINAL_STATUSES = ("applied", "failed", "cancelled", "discarded", "expired", "reverted")
DAILY_SETUP_LIMIT = 10

# Steps that must run again when a rules-only draft is upgraded with AI.
AI_UPGRADE_FROM = "extract_profile"
ALL_STEPS = pipeline.STEPS


async def _workspace_ids(session: Any) -> list[uuid.UUID]:
    return [row[0] for row in (await session.execute(text("SELECT scheduler_workspace_ids()")))]


def _system_ctx(session: Any, workspace_id: uuid.UUID) -> WorkspaceContext:
    return WorkspaceContext(
        session=session,
        user_id=uuid.UUID(int=0),
        workspace_id=workspace_id,
        role="system",
        request_id=None,
    )


def _today_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(UTC)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


async def get_setup(ctx: WorkspaceContext, draft_id: uuid.UUID) -> m.SetupDraft:
    row = await ctx.session.get(m.SetupDraft, draft_id)
    if row is None or row.workspace_id != ctx.workspace_id:
        raise AppError("setup_not_found", "Setup not found", 404)
    return row


async def get_open_setup(
    ctx: WorkspaceContext, profile_id: uuid.UUID | None = None
) -> m.SetupDraft | None:
    stmt = select(m.SetupDraft).where(m.SetupDraft.status.in_(OPEN_STATUSES))
    if profile_id is not None:
        stmt = stmt.where(m.SetupDraft.profile_id == profile_id)
    else:
        default = next(
            (p for p in await list_profiles(ctx) if p.is_default),
            None,
        )
        if default is None:
            return None
        stmt = stmt.where(m.SetupDraft.profile_id == default.id)
    return (
        (await ctx.session.execute(stmt.order_by(m.SetupDraft.created_at.desc()))).scalars().first()
    )


async def _resolve_profile(ctx: WorkspaceContext, body: s.SetupCreate) -> Any:
    if body.profile_id is not None:
        return await get_profile(ctx, body.profile_id)
    profiles = await list_profiles(ctx)
    if body.subject == "self":
        current = next((p for p in profiles if p.is_default), None) or (
            profiles[0] if profiles else None
        )
        if current is not None:
            return current
        return await create_profile(ctx, profile_schemas.ProfileCreate(display_name="My profile"))
    return await create_profile(ctx, profile_schemas.ProfileCreate(display_name="New person"))


async def _check_rate_limit(ctx: WorkspaceContext, now: datetime | None = None) -> None:
    from sqlalchemy import func

    used = int(
        (
            await ctx.session.execute(
                select(func.count())
                .select_from(m.SetupDraft)
                .where(m.SetupDraft.created_at >= _today_start(now))
            )
        ).scalar_one()
    )
    if used >= DAILY_SETUP_LIMIT:
        raise AppError(
            "setup_limit_reached",
            "You can start 10 setups a day. Try again tomorrow.",
            429,
            {"limit": DAILY_SETUP_LIMIT},
        )


async def _snapshot_base(ctx: WorkspaceContext, profile_id: uuid.UUID) -> dict[str, Any]:
    profile = await get_profile(ctx, profile_id)
    tracks = (
        await ctx.session.execute(
            select(Track.id).where(
                Track.profile_id == profile_id,
                Track.status == "active",
            )
        )
    ).scalars()
    answers = await list_answers(ctx, profile_id)
    return {
        "profile_updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        "track_ids": [str(t) for t in tracks],
        "answer_updated_at": {
            str(a.id): a.updated_at.isoformat() if a.updated_at else None for a in answers
        },
    }


async def _create(ctx: WorkspaceContext, body: s.SetupCreate, *, storage: Any) -> m.SetupDraft:
    profile = await _resolve_profile(ctx, body)
    open_draft = await get_open_setup(ctx, profile.id)
    if open_draft is not None:
        raise AppError(
            "setup_open_exists",
            "Finish the setup you already started.",
            409,
            {"draft_id": str(open_draft.id)},
        )
    await _check_rate_limit(ctx)

    if body.document_id is not None:
        document = await get_document(ctx, profile.id, body.document_id)
        if document.status != "ready" or not (document.extracted_text or "").strip():
            raise AppError(
                "setup_document_unreadable",
                "We could not read text from this file. Paste the text or try a Word file.",
                422,
            )
    else:
        if not (body.text or "").strip():
            raise AppError("setup_text_required", "Paste your resume text", 422)
        document = await create_text_document(ctx, profile.id, body.text or "", storage)

    mode = body.mode or ("update" if await profile_has_facts(ctx, profile.id) else "new")
    now = datetime.now(UTC)
    draft = m.SetupDraft(
        workspace_id=ctx.workspace_id,
        profile_id=profile.id,
        document_id=document.id,
        created_by=ctx.user_id,
        subject=body.subject,
        mode=mode,
        status="queued",
        role_text=(body.role_text or "").strip() or None,
        inputs={"timezone": body.timezone, "with_ai": body.with_ai},
        steps={},
        decisions={},
        base=await _snapshot_base(ctx, profile.id),
        expires_at=now + timedelta(days=OPEN_TTL_DAYS),
    )
    ctx.session.add(draft)
    try:
        await ctx.session.flush()
    except IntegrityError as exc:
        existing = await get_open_setup(ctx, profile.id)
        raise AppError(
            "setup_open_exists",
            "Finish the setup you already started.",
            409,
            {"draft_id": str(existing.id) if existing else None},
        ) from exc
    await audit.record(
        ctx,
        action="setup.started",
        target_type="setup_draft",
        target_id=str(draft.id),
        after={
            "profile_id": str(profile.id),
            "document_id": str(document.id),
            "subject": draft.subject,
            "mode": draft.mode,
            "with_ai": body.with_ai,
        },
    )
    return draft


async def create_setup(
    ctx: WorkspaceContext,
    body: s.SetupCreate,
    *,
    storage: Any,
    deps: pipeline.StepDeps,
    session_factory: Any = None,
    background: bool = False,
) -> m.SetupDraft:
    if background and session_factory is not None:
        # Commit the draft in its own transaction so the worker can see it.
        async with session_factory() as session, session.begin():
            await set_request_context(
                session, user_id=str(ctx.user_id), workspace_id=str(ctx.workspace_id)
            )
            worker_ctx = WorkspaceContext(
                session=session,
                user_id=ctx.user_id,
                workspace_id=ctx.workspace_id,
                role=ctx.role,
                request_id=ctx.request_id,
            )
            draft = await _create(worker_ctx, body, storage=storage)
            draft_id = draft.id
        pipeline.enqueue(draft_id, ctx, session_factory=session_factory, deps=deps)
        return await get_setup(ctx, draft_id)
    draft = await _create(ctx, body, storage=storage)
    draft = await pipeline.run_inline(ctx, draft, deps=deps)
    await ctx.session.refresh(draft)
    return draft


async def cancel_setup(ctx: WorkspaceContext, draft_id: uuid.UUID) -> m.SetupDraft:
    draft = await get_setup(ctx, draft_id)
    if draft.status not in ("queued", "running"):
        raise AppError("setup_not_running", "This setup is not running", 409)
    draft.status = "cancelled"
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="setup.cancelled",
        target_type="setup_draft",
        target_id=str(draft.id),
        after={"profile_id": str(draft.profile_id)},
    )
    await ctx.session.refresh(draft)
    return draft


async def discard_setup(ctx: WorkspaceContext, draft_id: uuid.UUID) -> m.SetupDraft:
    draft = await get_setup(ctx, draft_id)
    if draft.status not in ("ready", "failed", "cancelled"):
        raise AppError("setup_not_discardable", "This setup cannot be closed yet", 409)
    draft.status = "discarded"
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="setup.discarded",
        target_type="setup_draft",
        target_id=str(draft.id),
        after={"profile_id": str(draft.profile_id)},
    )
    await ctx.session.refresh(draft)
    return draft


def _reset_from(draft: m.SetupDraft, step: str) -> None:
    steps = dict(draft.steps or {})
    dropping = False
    for name in ALL_STEPS:
        if name == step:
            dropping = True
        if dropping:
            steps.pop(name, None)
    draft.steps = steps
    draft.bundle = None


async def _retry(ctx: WorkspaceContext, draft_id: uuid.UUID, *, with_ai: bool) -> m.SetupDraft:
    draft = await get_setup(ctx, draft_id)
    if draft.status == "ready":
        already_ai = (draft.steps or {}).get("extract_profile", {}).get("source") == "ai"
        if not with_ai or already_ai:
            raise AppError("setup_not_retryable", "There is nothing to read again", 409)
        _reset_from(draft, AI_UPGRADE_FROM)
    elif draft.status in ("failed", "cancelled"):
        failed_step = next(
            (
                name
                for name in ALL_STEPS
                if (draft.steps or {}).get(name, {}).get("status") == "failed"
            ),
            ALL_STEPS[0],
        )
        _reset_from(draft, failed_step)
    else:
        raise AppError("setup_not_retryable", "This setup cannot be retried", 409)

    if with_ai:
        draft.inputs = {**(draft.inputs or {}), "with_ai": True}
    draft.status = "queued"
    draft.error_code = None
    draft.expires_at = datetime.now(UTC) + timedelta(days=OPEN_TTL_DAYS)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="setup.started",
        target_type="setup_draft",
        target_id=str(draft.id),
        after={"profile_id": str(draft.profile_id), "retry": True, "with_ai": with_ai},
    )
    return draft


async def retry_setup(
    ctx: WorkspaceContext,
    draft_id: uuid.UUID,
    *,
    with_ai: bool,
    deps: pipeline.StepDeps,
    session_factory: Any = None,
    background: bool = False,
) -> m.SetupDraft:
    if background and session_factory is not None:
        # Commit the reset in its own transaction so the worker can see it.
        async with session_factory() as session, session.begin():
            await set_request_context(
                session, user_id=str(ctx.user_id), workspace_id=str(ctx.workspace_id)
            )
            worker_ctx = WorkspaceContext(
                session=session,
                user_id=ctx.user_id,
                workspace_id=ctx.workspace_id,
                role=ctx.role,
                request_id=ctx.request_id,
            )
            draft = await _retry(worker_ctx, draft_id, with_ai=with_ai)
            claimed_id = draft.id
        pipeline.enqueue(claimed_id, ctx, session_factory=session_factory, deps=deps)
        return await get_setup(ctx, claimed_id)
    draft = await _retry(ctx, draft_id, with_ai=with_ai)
    draft = await pipeline.run_inline(ctx, draft, deps=deps)
    await ctx.session.refresh(draft)
    return draft


# ---- retention -------------------------------------------------------------------------------


async def expire_setups(session_factory: Any, *, now: datetime | None = None) -> int:
    """Expire open drafts past their 14-day window. Content stays until the retention pass."""
    now = now or datetime.now(UTC)
    expired = 0
    async with session_factory() as session:
        workspace_ids = await _workspace_ids(session)
    for wid in workspace_ids:
        async with session_factory() as session, session.begin():
            await set_request_context(session, user_id=None, workspace_id=str(wid))
            rows = list(
                (
                    await session.execute(
                        select(m.SetupDraft).where(
                            m.SetupDraft.workspace_id == wid,
                            m.SetupDraft.status.in_(OPEN_STATUSES),
                            m.SetupDraft.expires_at.is_not(None),
                            m.SetupDraft.expires_at < now,
                        )
                    )
                )
                .scalars()
                .all()
            )
            if not rows:
                continue
            for row in rows:
                row.status = "expired"
            await audit.record(
                _system_ctx(session, wid),
                action="setup.expired",
                target_type="setup_draft",
                after={"count": len(rows), "ids": [str(r.id) for r in rows]},
                actor_type="system",
            )
            expired += len(rows)
    return expired


async def clear_setup_content(session_factory: Any, *, now: datetime | None = None) -> int:
    """Drop the personal data in finished drafts after 30 days; keep the metadata row."""
    now = now or datetime.now(UTC)
    cutoff = now - timedelta(days=CONTENT_RETENTION_DAYS)
    cleared = 0
    async with session_factory() as session:
        workspace_ids = await _workspace_ids(session)
    for wid in workspace_ids:
        async with session_factory() as session, session.begin():
            await set_request_context(session, user_id=None, workspace_id=str(wid))
            rows = [
                row
                for row in (
                    await session.execute(
                        select(m.SetupDraft).where(
                            m.SetupDraft.workspace_id == wid,
                            m.SetupDraft.status.in_(FINAL_STATUSES),
                            m.SetupDraft.updated_at < cutoff,
                        )
                    )
                )
                .scalars()
                .all()
                if row.bundle is not None or row.decisions
            ]
            if not rows:
                continue
            for row in rows:
                row.bundle = None
                row.decisions = {}
                row.result = None
                # Step records keep their status and timings; the values they carried go.
                steps = dict(row.steps or {})
                for step in ("stated_signals", "plan_searches", "normalize"):
                    record = steps.get(step)
                    if isinstance(record, dict):
                        for key in ("signals", "searches", "country", "sensitive_kinds"):
                            record.pop(key, None)
                row.steps = steps
                flag_modified(row, "steps")
            await audit.record(
                _system_ctx(session, wid),
                action="setup.content_cleared",
                target_type="setup_draft",
                after={"count": len(rows)},
                actor_type="system",
            )
            cleared += len(rows)
    return cleared


# ---- review decisions, validate, apply, revert ------------------------------------------------


def _bundle(draft: m.SetupDraft) -> s.SetupBundle:
    if draft.bundle is None:
        raise AppError("setup_not_ready", "This setup is still being read", 409)
    return s.SetupBundle.model_validate(draft.bundle)


def _decisions(draft: m.SetupDraft) -> s.SetupDecisions:
    return s.SetupDecisions.model_validate(draft.decisions or {})


def _allowed_item_ids(bundle: s.SetupBundle) -> set[str]:
    return {item.id for item in bundle.items} | {
        f"searches.{proposal.variant}" for proposal in bundle.searches
    }


async def patch_decisions(
    ctx: WorkspaceContext, draft_id: uuid.UUID, decisions: s.SetupDecisions
) -> m.SetupDraft:
    draft = await get_setup(ctx, draft_id)
    if draft.status != "ready":
        raise AppError("setup_not_ready", "This setup is not ready to review", 409)
    bundle = _bundle(draft)
    allowed = _allowed_item_ids(bundle)
    unknown = sorted(set(decisions.items) - allowed)
    if unknown:
        raise AppError(
            "setup_unknown_item",
            "Some choices belong to an older reading. Reload the review.",
            422,
            {"item_ids": unknown[:20]},
        )
    for item_id, decision in decisions.items.items():
        if decision.edited and decision.value is not None and not item_id.startswith("searches."):
            item = next((row for row in bundle.items if row.id == item_id), None)
            if item is None:
                continue
            value = decision.value
            if item.needs_you:
                value = apply_module._answer_payload(value)
            try:
                apply_module.validate_target(item.target, value)
            except Exception as exc:
                raise AppError(
                    "setup_invalid_value",
                    "That value does not fit this field.",
                    422,
                    {"item_id": item_id, "reason": str(exc)[:200]},
                ) from exc
    draft.decisions = decisions.model_dump(mode="json")
    await ctx.session.flush()
    await ctx.session.refresh(draft)
    # activity-log: N/A, review state on a draft; apply records the outcome.
    return draft


def _validate(ctx_free_errors: dict[str, str]) -> s.SetupValidateRead:
    return s.SetupValidateRead(ok=not ctx_free_errors, errors=ctx_free_errors)


async def validate_setup(ctx: WorkspaceContext, draft_id: uuid.UUID) -> s.SetupValidateRead:
    draft = await get_setup(ctx, draft_id)
    if draft.status != "ready":
        return s.SetupValidateRead(ok=False, errors={"setup": "This setup is not ready."})
    bundle = _bundle(draft)
    decisions = _decisions(draft)
    _writes, errors = apply_module.resolve(bundle, decisions)
    for proposal in apply_module.selected_searches(bundle, decisions):
        if proposal.blocked == "limit":
            errors[f"searches.{proposal.variant}"] = "The workspace search limit is reached."
        elif proposal.blocked == "duplicate":
            errors[f"searches.{proposal.variant}"] = "A similar search already exists."
    return _validate(errors)


async def _stale_item_ids(
    ctx: WorkspaceContext, draft: m.SetupDraft, bundle: s.SetupBundle, decisions: s.SetupDecisions
) -> list[str]:
    base = draft.base or {}
    stale: list[str] = []
    profile = await get_profile(ctx, draft.profile_id)
    profile_updated = profile.updated_at.isoformat() if profile.updated_at else None
    if profile_updated != base.get("profile_updated_at"):
        stale.extend(
            item.id
            for item in bundle.items
            if item.group == "profile" and item.target in apply_module.HEADER_TARGETS
        )

    active = [
        str(row)
        for row in (
            await ctx.session.execute(
                select(Track.id).where(
                    Track.profile_id == draft.profile_id,
                    Track.status == "active",
                )
            )
        ).scalars()
    ]
    if sorted(active) != sorted(base.get("track_ids") or []):
        stale.extend(f"searches.{proposal.variant}" for proposal in bundle.searches)

    answer_base = base.get("answer_updated_at") or {}
    if answer_base:
        from app.profiles.models import AnswerBank

        rows = (
            await ctx.session.execute(
                select(AnswerBank).where(
                    AnswerBank.id.in_([uuid.UUID(str(i)) for i in answer_base])
                )
            )
        ).scalars()
        for row in rows:
            current = row.updated_at.isoformat() if row.updated_at else None
            if current != answer_base.get(str(row.id)):
                stale.append(f"answers.{row.key}" + (f".{row.country}" if row.country else ""))
    return sorted(set(stale))


async def apply_setup(
    ctx: WorkspaceContext,
    draft_id: uuid.UUID,
    *,
    apply_key: str,
    start_first_run: bool,
    settings: Any,
    session_factory: Any,
) -> s.SetupApplyRead:
    """Apply in one committed transaction, then run the after-commit jobs outside it."""
    if not apply_key or len(apply_key) > 64:
        raise AppError("idempotency_key_required", "Send an Idempotency-Key header", 422)

    outcome: apply_module.ApplyOutcome | None = None
    async with session_factory() as session, session.begin():
        await set_request_context(
            session, user_id=str(ctx.user_id), workspace_id=str(ctx.workspace_id)
        )
        worker = WorkspaceContext(
            session=session,
            user_id=ctx.user_id,
            workspace_id=ctx.workspace_id,
            role=ctx.role,
            request_id=ctx.request_id,
        )
        draft = (
            await session.execute(
                select(m.SetupDraft)
                .where(
                    m.SetupDraft.id == draft_id,
                    m.SetupDraft.workspace_id == ctx.workspace_id,
                )
                .with_for_update()
            )
        ).scalar_one_or_none()
        if draft is None:
            raise AppError("setup_not_found", "Setup not found", 404)
        if draft.status == "applied":
            if draft.apply_key == apply_key and draft.result:
                return _apply_read(draft, draft.result)
            raise AppError("setup_already_applied", "This setup was already applied", 409)
        if draft.status == "applying":
            raise AppError("setup_apply_in_progress", "This setup is already being applied", 409)
        if draft.status != "ready":
            raise AppError("setup_not_ready", "This setup is not ready to apply", 409)

        bundle = _bundle(draft)
        decisions = _decisions(draft)
        stale = await _stale_item_ids(worker, draft, bundle, decisions)
        if stale:
            raise AppError(
                "setup_stale",
                "Some values changed since we read your resume. Refresh those rows.",
                409,
                {"item_ids": stale[:40]},
            )
        _writes, errors = apply_module.resolve(bundle, decisions)
        if errors:
            raise AppError(
                "setup_invalid_items",
                "Some values need a fix before saving",
                422,
                {"items": errors},
            )
        draft.status = "applying"
        await session.flush()
        outcome = await apply_module.apply_bundle(worker, draft, bundle, decisions)
        needs_you = 0
        for item in bundle.items:
            if not item.needs_you:
                continue
            decision = decisions.items.get(item.id)
            value = decision.value if decision is not None and decision.edited else item.value
            if value in (None, "", [], {}):
                needs_you += 1
        result = {
            "needs_you": needs_you,
            "created": {key: [str(i) for i in ids] for key, ids in outcome.created.items()},
            "updated": {key: [str(i) for i in ids] for key, ids in outcome.updated.items()},
            "counts": outcome.counts,
            "needs_you": int(((draft.bundle or {}).get("counts") or {}).get("needs_you", 0)),
            "links": outcome.links,
            "before": outcome.before,
            "written": outcome.written,
            "needs_you": int((draft.bundle or {}).get("counts", {}).get("needs_you", 0)),
        }
        draft.result = result
        draft.apply_key = apply_key
        draft.applied_at = outcome.applied_at
        draft.status = "applied"
        draft.expires_at = outcome.applied_at + timedelta(days=14)
        await session.flush()
        await audit.record(
            worker,
            action="setup.applied",
            target_type="setup_draft",
            target_id=str(draft.id),
            after={
                "profile_id": str(draft.profile_id),
                "counts": outcome.counts,
                "created": {key: len(ids) for key, ids in outcome.created.items()},
                "updated": {key: len(ids) for key, ids in outcome.updated.items()},
            },
        )

    if outcome is not None:
        await _after_commit(
            settings,
            session_factory,
            outcome,
            start_first_run=start_first_run,
            user_id=ctx.user_id,
            workspace_id=ctx.workspace_id,
            role=ctx.role,
            request_id=ctx.request_id,
        )
        return s.SetupApplyRead(
            draft_id=outcome.draft_id,
            profile_id=outcome.profile_id,
            applied_at=outcome.applied_at,
            created=outcome.created,
            updated=outcome.updated,
            counts=outcome.counts,
            links=outcome.links,
        )
    raise AppError("setup_apply_failed", "The setup could not be applied", 500)


def _apply_read(draft: m.SetupDraft, result: dict[str, Any]) -> s.SetupApplyRead:
    return s.SetupApplyRead(
        draft_id=draft.id,
        profile_id=draft.profile_id,
        applied_at=draft.applied_at or datetime.now(UTC),
        created={
            key: [uuid.UUID(str(i)) for i in ids]
            for key, ids in (result.get("created") or {}).items()
        },
        updated={
            key: [uuid.UUID(str(i)) for i in ids]
            for key, ids in (result.get("updated") or {}).items()
        },
        counts=result.get("counts") or {},
        links=result.get("links") or {},
    )


async def _after_commit(
    settings: Any,
    session_factory: Any,
    outcome: apply_module.ApplyOutcome,
    *,
    start_first_run: bool,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    role: str,
    request_id: str | None,
) -> None:
    import logging

    log = logging.getLogger(__name__)
    for track_id in outcome.search_ids:
        try:
            async with session_factory() as session, session.begin():
                await set_request_context(
                    session, user_id=str(user_id), workspace_id=str(workspace_id)
                )
                worker = WorkspaceContext(
                    session=session,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    role=role,
                    request_id=request_id,
                )
                from app.gaps.service import refresh_suggestions

                await refresh_suggestions(worker, track_id)
        except Exception:
            log.exception("setup_gap_refresh_failed track=%s", track_id)

    if (
        not start_first_run
        or not outcome.search_ids
        or getattr(settings, "environment", "test") not in {"dev", "prod"}
    ):
        return
    try:
        async with session_factory() as session:
            await set_request_context(session, user_id=str(user_id), workspace_id=str(workspace_id))
            worker = WorkspaceContext(
                session=session,
                user_id=user_id,
                workspace_id=workspace_id,
                role=role,
                request_id=request_id,
            )
            from app.sources.service import start_discovery

            await start_discovery(
                worker,
                outcome.search_ids[0],
                background=True,
                session_factory=session_factory,
            )
    except Exception:
        log.exception("setup_first_run_failed")


async def revert_setup(ctx: WorkspaceContext, draft_id: uuid.UUID) -> s.SetupRevertRead:
    draft = await get_setup(ctx, draft_id)
    if draft.status != "applied":
        raise AppError("setup_not_applied", "This setup was not applied", 409)
    removed, kept = await apply_module.revert_bundle(ctx, draft)
    draft.status = "reverted"
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="setup.reverted",
        target_type="setup_draft",
        target_id=str(draft.id),
        after={"profile_id": str(draft.profile_id), "removed": removed, "kept": len(kept)},
    )
    return s.SetupRevertRead(draft_id=draft.id, removed=removed, kept=kept)


async def mark_seen(ctx: WorkspaceContext, draft_id: uuid.UUID, page: str) -> m.SetupDraft:
    draft = await get_setup(ctx, draft_id)
    decisions = _decisions(draft)
    pages = sorted({*decisions.seen_pages, page})
    draft.decisions = decisions.model_copy(update={"seen_pages": pages}).model_dump(mode="json")
    await ctx.session.flush()
    await ctx.session.refresh(draft)
    # activity-log: N/A, a UI marker dismissal on the draft, no domain change.
    return draft


async def provenance(ctx: WorkspaceContext, profile_id: uuid.UUID) -> s.SetupProvenanceRead | None:
    stmt = (
        select(m.SetupDraft)
        .where(
            m.SetupDraft.profile_id == profile_id,
            m.SetupDraft.status == "applied",
        )
        .order_by(m.SetupDraft.applied_at.desc())
        .limit(1)
    )
    draft = (await ctx.session.execute(stmt)).scalars().first()
    if draft is None or draft.applied_at is None:
        return None
    result = draft.result or {}
    return s.SetupProvenanceRead(
        draft_id=draft.id,
        profile_id=draft.profile_id,
        applied_at=draft.applied_at,
        created={
            key: [uuid.UUID(str(i)) for i in ids]
            for key, ids in (result.get("created") or {}).items()
        },
        updated={
            key: [uuid.UUID(str(i)) for i in ids]
            for key, ids in (result.get("updated") or {}).items()
        },
        seen_pages=list((draft.decisions or {}).get("seen_pages") or []),
    )
