"""Setup pipeline: checkpointed steps from one resume document to a review bundle.

Steps write to `steps` before the next starts, so a retry resumes at the first unfinished step.
Intermediate results that cost an AI call (stated signals, search proposals) are checkpointed in
`steps` and cleared with the bundle by the retention job. Background mode commits each step in its
own transaction; tests run the same steps inline and see a finished draft.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from time import perf_counter
from typing import Any

from pydantic_ai import PromptedOutput
from sqlalchemy import select, text

from app.ai import prompts as prompt_registry
from app.ai import service as ai
from app.audit import service as audit
from app.auth.models import User
from app.core.config import Settings
from app.core.errors import AppError
from app.core.rls import set_request_context
from app.core.security import WorkspaceContext
from app.core.storage import ObjectStorage
from app.onboarding import apply as apply_module
from app.onboarding import bundle as bundle_builder
from app.onboarding import grounding
from app.onboarding import models as m
from app.onboarding import schemas as s
from app.onboarding.derive import prefs
from app.onboarding.derive import searches as search_rules
from app.onboarding.parse import detect_language, looks_like_resume
from app.onboarding.sensitive_lines import strip_sensitive_lines
from app.profiles import models as profile_models
from app.profiles import parse as parse_service
from app.profiles.parse_schema import ProfileExtract
from app.taxonomy.aliases import skill_key
from app.tracks.models import Track, TrackCriteria

log = logging.getLogger(__name__)

STEPS: tuple[str, ...] = (
    "read_file",
    "check_document",
    "extract_profile",
    "stated_signals",
    "normalize",
    "plan_searches",
    "draft_rest",
    "ground_and_build",
)
AI_STEPS = frozenset({"extract_profile", "stated_signals", "plan_searches", "draft_rest"})
STEP_TIMEOUT_SECONDS = 60
SETUP_AI_ESTIMATE_MICROS = 150_000  # 15 cents for a two-page resume across three calls
STALE_AFTER = timedelta(minutes=3)
OPEN_STATUSES = ("queued", "running")
_BACKGROUND_TASKS: set[asyncio.Task] = set()

_AI_FALLBACK_CODES = {
    "ai_not_configured",
    "budget_reached",
    "ai_credential_invalid",
    "ai_provider_error",
    "ai_restricted",
}


class SetupStepFailed(Exception):
    def __init__(self, code: str, step: str) -> None:
        super().__init__(code)
        self.code = code
        self.step = step


@dataclass
class StepDeps:
    settings: Settings
    storage: ObjectStorage
    run_structured: Any = None
    model_factory: Any = None


def steps_of(draft: m.SetupDraft) -> dict[str, Any]:
    return dict(draft.steps or {})


def step_done(draft: m.SetupDraft, step: str) -> bool:
    return steps_of(draft).get(step, {}).get("status") in {"done", "skipped"}


def _mark(draft: m.SetupDraft, step: str, *, status: str, **extra: Any) -> None:
    steps = steps_of(draft)
    record = dict(steps.get(step) or {})
    record.update(extra)
    record["status"] = status
    record["ended_at"] = datetime.now(UTC).isoformat()
    steps[step] = record
    draft.steps = steps


def _started(draft: m.SetupDraft, step: str) -> None:
    steps = steps_of(draft)
    record = dict(steps.get(step) or {})
    record["status"] = "running"
    record["started_at"] = datetime.now(UTC).isoformat()
    steps[step] = record
    draft.steps = steps


async def _document(ctx: WorkspaceContext, draft: m.SetupDraft) -> profile_models.Document:
    if draft.document_id is None:
        raise SetupStepFailed("setup_document_missing", "read_file")
    document = await ctx.session.get(profile_models.Document, draft.document_id)
    if document is None or document.profile_id != draft.profile_id:
        raise SetupStepFailed("setup_document_missing", "read_file")
    return document


def _safe_text(document: profile_models.Document) -> str:
    return strip_sensitive_lines(document.extracted_text or "").text


def _parsed(document: profile_models.Document) -> ProfileExtract | None:
    if not document.parsed:
        return None
    try:
        return ProfileExtract.model_validate(document.parsed)
    except Exception:
        log.warning("setup_parsed_draft_invalid document=%s", document.id)
        return None


def _reading(draft: m.SetupDraft, document: profile_models.Document) -> bundle_builder.Reading:
    parsed = _parsed(document)
    return bundle_builder.read_resume(
        _safe_text(document),
        parsed=parsed.model_dump(mode="json") if parsed else None,
        source=str(steps_of(draft).get("extract_profile", {}).get("source") or "rules"),
    )


def _ordered_experiences(reading: bundle_builder.Reading) -> list[dict[str, Any]]:
    def start(exp: dict[str, Any]) -> str:
        return str(exp.get("start_date") or "")

    return sorted(reading.experiences, key=start, reverse=True)


async def _step_read_file(
    ctx: WorkspaceContext, draft: m.SetupDraft, deps: StepDeps
) -> dict[str, Any]:
    document = await _document(ctx, draft)
    warnings = [str(w.get("code")) for w in document.warnings or [] if isinstance(w, dict)]
    if document.status != "ready" or not (document.extracted_text or "").strip():
        code = "needs_ocr" if "needs_ocr" in warnings else "setup_document_unreadable"
        raise SetupStepFailed(code, "read_file")
    return {"chars": len(document.extracted_text or ""), "warning_codes": warnings}


async def _step_check_document(
    ctx: WorkspaceContext, draft: m.SetupDraft, deps: StepDeps
) -> dict[str, Any]:
    document = await _document(ctx, draft)
    filtered = strip_sensitive_lines(document.extracted_text or "")
    warnings = [str(w.get("code")) for w in document.warnings or [] if isinstance(w, dict)]
    return {
        "resume_like": looks_like_resume(filtered.text),
        "language": detect_language(filtered.text),
        "sensitive_removed": filtered.removed,
        "sensitive_kinds": list(filtered.kinds),
        "injection_removed": "injection_lines_removed" in warnings,
    }


async def _step_extract_profile(
    ctx: WorkspaceContext, draft: m.SetupDraft, deps: StepDeps
) -> dict[str, Any]:
    document = await _document(ctx, draft)
    with_ai = bool((draft.inputs or {}).get("with_ai", True))
    if not with_ai:
        return {"source": "rules", "reason": "ai_off"}
    try:
        await ai.check_budget(ctx, SETUP_AI_ESTIMATE_MICROS)
        await asyncio.wait_for(
            parse_service.parse_document(
                ctx,
                deps.settings,
                draft.profile_id,
                document.id,
                model_factory=deps.model_factory,
                run_structured=deps.run_structured,
            ),
            timeout=STEP_TIMEOUT_SECONDS,
        )
        return {"source": "ai", "prompt_version": parse_service.PROMPT.key}
    except TimeoutError:
        return {"source": "rules", "reason": "ai_timeout"}
    except AppError as exc:
        if exc.code in _AI_FALLBACK_CODES:
            return {"source": "rules", "reason": exc.code}
        raise
    except Exception:
        log.exception("setup_extract_failed draft=%s", draft.id)
        return {"source": "rules", "reason": "ai_provider_error"}


async def _step_stated_signals(
    ctx: WorkspaceContext, draft: m.SetupDraft, deps: StepDeps
) -> dict[str, Any]:
    document = await _document(ctx, draft)
    text = _safe_text(document)
    basics = bundle_builder.read_resume(text)
    signals = prefs.collect(text, resume_country=basics.country)
    source = "rules"
    reason = ""
    if bool((draft.inputs or {}).get("with_ai", True)):
        runner: Any = deps.run_structured or ai.run_structured
        prompt = (
            "Read explicit statements from this resume.\n"
            "<<<UNTRUSTED_RESUME_TEXT>>>\n"
            f"{text[:60_000]}\n"
            "<<<END_UNTRUSTED_RESUME_TEXT>>>"
        )
        try:
            result = await asyncio.wait_for(
                runner(
                    ctx,
                    deps.settings,
                    tier="bulk",
                    feature="setup_signals",
                    system=prompt_registry.SETUP_SIGNALS.system,
                    prompt=prompt,
                    output_type=PromptedOutput(s.SetupSignalsOut),
                    max_output_tokens=800,
                    model_factory=deps.model_factory,
                ),
                timeout=STEP_TIMEOUT_SECONDS,
            )
            raw = [item.model_dump() for item in result.output.signals]
            signals = prefs.merge_ai(signals, raw, text)
            source = "ai"
        except TimeoutError:
            reason = "ai_timeout"
        except AppError as exc:
            if exc.code not in _AI_FALLBACK_CODES:
                raise
            reason = exc.code
        except Exception:
            log.exception("setup_signals_failed draft=%s", draft.id)
            reason = "ai_provider_error"
    return {
        "source": source,
        "reason": reason,
        "count": len(signals),
        "signals": [
            {
                "kind": signal.kind,
                "value": signal.value,
                "quote": signal.quote,
                "start": signal.start,
                "end": signal.end,
                "country": signal.country,
                "currency": signal.currency,
                "period": signal.period,
                "confidence": signal.confidence,
                "stale": signal.stale,
            }
            for signal in signals
        ],
    }


def _signals_from(draft: m.SetupDraft) -> list[prefs.Signal]:
    raw = steps_of(draft).get("stated_signals", {}).get("signals") or []
    out: list[prefs.Signal] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        out.append(
            prefs.Signal(
                kind=str(item.get("kind") or ""),
                value=str(item.get("value") or ""),
                quote=str(item.get("quote") or ""),
                start=int(item.get("start") or 0),
                end=int(item.get("end") or 0),
                country=item.get("country"),
                currency=item.get("currency"),
                period=item.get("period"),
                confidence=float(item.get("confidence") or 0.7),
                stale=bool(item.get("stale")),
            )
        )
    return out


async def _step_normalize(
    ctx: WorkspaceContext, draft: m.SetupDraft, deps: StepDeps
) -> dict[str, Any]:
    document = await _document(ctx, draft)
    reading = _reading(draft, document)
    return {
        "country": reading.country,
        "skills": len(reading.skills),
        "roles": len(reading.experiences),
        "has_headline": bool(reading.headline),
    }


def _v2_prompt(role_text: str, context: dict[str, Any]) -> str:
    return (
        "<<<UNTRUSTED_ROLE_TEXT>>>\n"
        f"{role_text.strip()[:2000]}\n"
        "<<<END_UNTRUSTED_ROLE_TEXT>>>\n\n"
        "<<<PROFILE_CONTEXT>>>\n"
        f"{json.dumps(context, ensure_ascii=False)[:6000]}\n"
        "<<<END_PROFILE_CONTEXT>>>"
    )


def _title_keys(proposal: s.SearchProposal) -> set[str]:
    return {
        skill_key(spec.title)
        for spec in proposal.criteria.titles
        if not spec.exclude and spec.title
    }


def _overlap(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


async def _mark_duplicates(
    ctx: WorkspaceContext, draft: m.SetupDraft, proposals: list[s.SearchProposal]
) -> None:
    rows = (
        await ctx.session.execute(
            select(Track.id, TrackCriteria.structured)
            .join(TrackCriteria, TrackCriteria.track_id == Track.id)
            .where(
                Track.profile_id == draft.profile_id,
                Track.status == "active",
            )
        )
    ).all()
    if not rows:
        return
    for proposal in proposals:
        keys = _title_keys(proposal)
        for track_id, structured in rows:
            title_specs = (structured or {}).get("titles") or []
            existing = {
                skill_key(str(spec.get("title") or ""))
                for spec in title_specs
                if isinstance(spec, dict) and spec.get("title") and not spec.get("exclude")
            }
            if _overlap(keys, existing) >= 0.7:
                proposal.duplicate_of = track_id
                break


async def _step_plan_searches(
    ctx: WorkspaceContext, draft: m.SetupDraft, deps: StepDeps
) -> dict[str, Any]:
    document = await _document(ctx, draft)
    reading = _reading(draft, document)
    experiences = _ordered_experiences(reading)
    role_text = (draft.role_text or "").strip()
    if not experiences and not role_text and not reading.headline:
        return {"status": "skipped", "source": "skipped", "reason": "no_role_signal"}

    inp = search_rules.SearchInput(
        experiences=experiences,
        headline=reading.headline,
        location=reading.location,
        country=reading.country,
        # Only skills the resume actually states may become a must-have (P1).
        profile_skills=[
            name for name in reading.skills if grounding.quote_found(reading.text, name)
        ],
        role_text=role_text,
        device_timezone=str((draft.inputs or {}).get("timezone") or "UTC"),
    )
    proposals = search_rules.build_all(inp)
    source = "rules"
    reason = ""
    if proposals and bool((draft.inputs or {}).get("with_ai", True)):
        context = {
            "headline": reading.headline,
            "latest_title": str(experiences[0].get("title") or "") if experiences else "",
            "years": len(experiences),
            "skills": reading.skills[:30],
            "country": reading.country,
            "variants": [proposal.variant for proposal in proposals],
        }
        runner: Any = deps.run_structured or ai.run_structured
        try:
            result = await asyncio.wait_for(
                runner(
                    ctx,
                    deps.settings,
                    tier="standard",
                    feature="search_plan_v2",
                    system=prompt_registry.SEARCH_PLAN_V2.system,
                    prompt=_v2_prompt(role_text or str(experiences[0].get("title") or ""), context),
                    output_type=PromptedOutput(s.SearchPlanV2Out),
                    max_output_tokens=1800,
                    model_factory=deps.model_factory,
                ),
                timeout=STEP_TIMEOUT_SECONDS,
            )
            proposals = search_rules.apply_model(
                proposals, [item.model_dump() for item in result.output.variants], inp
            )
            source = "ai"
        except TimeoutError:
            reason = "ai_timeout"
        except AppError as exc:
            if exc.code not in _AI_FALLBACK_CODES:
                raise
            reason = exc.code
        except Exception:
            log.exception("setup_search_plan_failed draft=%s", draft.id)
            reason = "ai_provider_error"

    await _mark_duplicates(ctx, draft, proposals)
    return {
        "source": source,
        "reason": reason,
        "count": len(proposals),
        "searches": [proposal.model_dump(mode="json") for proposal in proposals],
    }


async def _step_draft_rest(
    ctx: WorkspaceContext, draft: m.SetupDraft, deps: StepDeps
) -> dict[str, Any]:
    # Writing style and Studio are deterministic and built with the bundle. Starter answers need
    # profile facts, so they run after apply through the answer desk (recorded in the plan).
    return {"status": "skipped", "source": "rules", "reason": "after_apply"}


async def _step_ground_and_build(
    ctx: WorkspaceContext, draft: m.SetupDraft, deps: StepDeps
) -> dict[str, Any]:
    document = await _document(ctx, draft)
    reading = _reading(draft, document)
    steps = steps_of(draft)
    searches = [
        s.SearchProposal.model_validate(raw)
        for raw in steps.get("plan_searches", {}).get("searches") or []
    ]
    check = steps.get("check_document", {})
    notices: list[str] = []
    if check.get("resume_like") is False:
        notices.append("not_resume_like")
    if int(check.get("sensitive_removed") or 0) > 0:
        notices.append("sensitive_lines_removed")
    if check.get("injection_removed"):
        notices.append("injection_lines_removed")
    user = await ctx.session.get(User, ctx.user_id)
    built = bundle_builder.build_bundle(
        reading=reading,
        document_id=document.id,
        signals=_signals_from(draft),
        searches=searches,
        subject=draft.subject,
        user=user,
        device_timezone=str((draft.inputs or {}).get("timezone") or "UTC"),
        notices=notices,
    )
    grounded, dropped = grounding.ground_bundle(built, reading.text)
    if draft.mode == "update":
        grounded = await apply_module.annotate_current(ctx, draft, grounded)
    draft.bundle = grounded.model_dump(mode="json")
    return {
        "items": len(grounded.items),
        "searches": len(grounded.searches),
        "needs_you": grounded.counts.get("needs_you", 0),
        "dropped": dropped,
    }


_STEP_FUNCS = {
    "read_file": _step_read_file,
    "check_document": _step_check_document,
    "extract_profile": _step_extract_profile,
    "stated_signals": _step_stated_signals,
    "normalize": _step_normalize,
    "plan_searches": _step_plan_searches,
    "draft_rest": _step_draft_rest,
    "ground_and_build": _step_ground_and_build,
}


async def _run_step(ctx: WorkspaceContext, draft: m.SetupDraft, step: str, deps: StepDeps) -> None:
    _started(draft, step)
    started = perf_counter()
    try:
        record = await _STEP_FUNCS[step](ctx, draft, deps)
    except SetupStepFailed as exc:
        _mark(
            draft,
            step,
            status="failed",
            reason=exc.code,
            duration_ms=int((perf_counter() - started) * 1000),
        )
        raise
    except Exception as exc:
        log.exception("setup_step_crashed draft=%s step=%s", draft.id, step)
        _mark(
            draft,
            step,
            status="failed",
            reason="setup_build_failed",
            duration_ms=int((perf_counter() - started) * 1000),
        )
        raise SetupStepFailed("setup_build_failed", step) from exc
    record.setdefault("duration_ms", int((perf_counter() - started) * 1000))
    _mark(draft, step, status=str(record.pop("status", "done")), **record)


def _step_sources(draft: m.SetupDraft) -> dict[str, str]:
    return {
        step: str(record.get("source") or "")
        for step, record in steps_of(draft).items()
        if isinstance(record, dict)
    }


async def _finish(ctx: WorkspaceContext, draft: m.SetupDraft) -> None:
    draft.status = "ready"
    draft.error_code = None
    draft.expires_at = datetime.now(UTC) + timedelta(days=14)
    await ctx.session.flush()
    counts = dict((draft.bundle or {}).get("counts") or {})
    await audit.record(
        ctx,
        action="setup.ready",
        target_type="setup_draft",
        target_id=str(draft.id),
        after={
            "profile_id": str(draft.profile_id),
            "document_id": str(draft.document_id) if draft.document_id else None,
            "subject": draft.subject,
            "mode": draft.mode,
            "counts": counts,
            "sources": _step_sources(draft),
        },
    )


async def _fail(ctx: WorkspaceContext, draft: m.SetupDraft, exc: SetupStepFailed) -> None:
    draft.status = "failed"
    draft.error_code = exc.code
    if draft.expires_at is None:
        draft.expires_at = datetime.now(UTC) + timedelta(days=14)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="setup.failed",
        target_type="setup_draft",
        target_id=str(draft.id),
        after={"profile_id": str(draft.profile_id), "step": exc.step, "code": exc.code},
    )


async def run_inline(ctx: WorkspaceContext, draft: m.SetupDraft, *, deps: StepDeps) -> m.SetupDraft:
    """Run every unfinished step in the caller's transaction (tests and local dev)."""
    if draft.status not in OPEN_STATUSES:
        return draft
    draft.status = "running"
    await ctx.session.flush()
    try:
        for step in STEPS:
            if step_done(draft, step):
                continue
            await _run_step(ctx, draft, step, deps)
            await ctx.session.flush()
        await _finish(ctx, draft)
    except SetupStepFailed as exc:
        await _fail(ctx, draft, exc)
    return draft


async def _background(
    session_factory: Any,
    draft_id: uuid.UUID,
    *,
    user_id: uuid.UUID,
    workspace_id: uuid.UUID,
    role: str,
    request_id: str | None,
    deps: StepDeps,
) -> None:
    try:
        for step in STEPS:
            async with session_factory() as session, session.begin():
                await set_request_context(
                    session, user_id=str(user_id), workspace_id=str(workspace_id)
                )
                ctx = WorkspaceContext(
                    session=session,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    role=role,
                    request_id=request_id,
                )
                draft = await session.get(m.SetupDraft, draft_id)
                if draft is None:
                    return
                if draft.status == "queued":
                    draft.status = "running"
                elif draft.status != "running":
                    return
                if step_done(draft, step):
                    continue
                try:
                    await _run_step(ctx, draft, step, deps)
                except SetupStepFailed as exc:
                    await _fail(ctx, draft, exc)
                    return
        async with session_factory() as session, session.begin():
            await set_request_context(session, user_id=str(user_id), workspace_id=str(workspace_id))
            ctx = WorkspaceContext(
                session=session,
                user_id=user_id,
                workspace_id=workspace_id,
                role=role,
                request_id=request_id,
            )
            draft = await session.get(m.SetupDraft, draft_id)
            if draft is not None and draft.status == "running":
                await _finish(ctx, draft)
    except Exception:
        log.exception("setup_background_failed draft=%s", draft_id)
        try:
            async with session_factory() as session, session.begin():
                await set_request_context(
                    session, user_id=str(user_id), workspace_id=str(workspace_id)
                )
                draft = await session.get(m.SetupDraft, draft_id)
                if draft is not None and draft.status in OPEN_STATUSES:
                    draft.status = "failed"
                    draft.error_code = "setup_build_failed"
        except Exception:
            log.exception("setup_background_cleanup_failed draft=%s", draft_id)


def enqueue(
    draft_id: uuid.UUID, ctx: WorkspaceContext, *, session_factory: Any, deps: StepDeps
) -> None:
    task = asyncio.create_task(
        _background(
            session_factory,
            draft_id,
            user_id=ctx.user_id,
            workspace_id=ctx.workspace_id,
            role=ctx.role,
            request_id=ctx.request_id,
            deps=deps,
        )
    )
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)


async def reap_stale_setups(session_factory: Any, *, now: datetime | None = None) -> int:
    """Fail drafts whose worker never started or stopped reporting progress (API restart)."""
    now = now or datetime.now(UTC)
    cutoff = now - STALE_AFTER
    reaped = 0
    async with session_factory() as session:
        workspace_ids = [
            row[0] for row in (await session.execute(text("SELECT scheduler_workspace_ids()")))
        ]
    for wid in workspace_ids:
        async with session_factory() as session, session.begin():
            await set_request_context(session, user_id=None, workspace_id=str(wid))
            rows = list(
                (
                    await session.execute(
                        select(m.SetupDraft).where(
                            m.SetupDraft.workspace_id == wid,
                            m.SetupDraft.status.in_(OPEN_STATUSES),
                            m.SetupDraft.updated_at < cutoff,
                        )
                    )
                )
                .scalars()
                .all()
            )
            if not rows:
                continue
            for row in rows:
                row.status = "failed"
                row.error_code = "setup_interrupted"
            await audit.record(
                WorkspaceContext(
                    session=session,
                    user_id=uuid.UUID(int=0),
                    workspace_id=wid,
                    role="system",
                    request_id=None,
                ),
                action="setup.failed",
                target_type="setup_draft",
                after={"count": len(rows), "code": "setup_interrupted"},
                actor_type="system",
            )
            reaped += len(rows)
    return reaped


__all__ = [
    "AI_STEPS",
    "SETUP_AI_ESTIMATE_MICROS",
    "STEPS",
    "SetupStepFailed",
    "StepDeps",
    "ai",
    "enqueue",
    "reap_stale_setups",
    "run_inline",
    "step_done",
    "steps_of",
]
