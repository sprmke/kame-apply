"""Answer Desk orchestration: parse → resolve → persist."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from app.answers import draft as drafting
from app.answers import match as matching
from app.answers import restriction as restr
from app.answers import schemas as s
from app.answers import split as splitter
from app.answers.models import AnswerDeskItem, AnswerDeskSession
from app.applications.models import Application
from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.profiles import models as pm
from app.profiles import schemas as ps
from app.profiles.answers import create_answer
from app.profiles.service import get_profile


async def _profile_bundle(ctx: WorkspaceContext, profile_id: uuid.UUID) -> dict[str, Any]:
    profile = await get_profile(ctx, profile_id)
    exps = list(
        (
            await ctx.session.execute(
                select(pm.Experience)
                .where(pm.Experience.profile_id == profile_id)
                .order_by(pm.Experience.sort_order.asc())
                .limit(8)
            )
        )
        .scalars()
        .all()
    )
    skills = list(
        (
            await ctx.session.execute(
                select(pm.Skill).where(pm.Skill.profile_id == profile_id).limit(24)
            )
        )
        .scalars()
        .all()
    )
    voice = (
        await ctx.session.execute(
            select(pm.VoiceProfile).where(pm.VoiceProfile.profile_id == profile_id).limit(1)
        )
    ).scalar_one_or_none()
    return {
        "id": str(profile.id),
        "display_name": profile.display_name,
        "headline": profile.headline,
        "summary": profile.summary,
        "location": profile.location,
        "work_authorization": profile.work_authorization or {},
        "experiences": [{"title": e.title, "company": e.company, "id": str(e.id)} for e in exps],
        "skills": [{"name": sk.name, "id": str(sk.id)} for sk in skills],
        "voice": {
            "style": (voice.style if voice else {}) or {},
            "banned_phrases": list((voice.banned_phrases if voice else None) or []),
            "ai_use_stance": (voice.ai_use_stance if voice else "") or "",
        },
    }


def _item_dict(row: AnswerDeskItem) -> dict[str, Any]:
    return {
        "id": row.id,
        "session_id": row.session_id,
        "sort_order": row.sort_order,
        "question": row.question,
        "constraints": row.constraints or {},
        "ai_restricted": row.ai_restricted,
        "legal_flag": row.legal_flag,
        "source": row.source,
        "draft": row.draft or "",
        "fact_notes": row.fact_notes or [],
        "evidence_refs": row.evidence_refs or [],
        "banned_hits": list(row.banned_hits or []),
        "char_limit": row.char_limit,
        "format": row.format,
        "answer_bank_id": row.answer_bank_id,
        "from_answer_bank": row.source == "bank",
        "message": "",
    }


async def _session_read(ctx: WorkspaceContext, session_id: uuid.UUID) -> dict[str, Any]:
    sess = await ctx.session.get(AnswerDeskSession, session_id)
    if sess is None or sess.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Answer Desk session not found", 404)
    items = list(
        (
            await ctx.session.execute(
                select(AnswerDeskItem)
                .where(AnswerDeskItem.session_id == sess.id)
                .order_by(AnswerDeskItem.sort_order.asc())
            )
        )
        .scalars()
        .all()
    )
    return {
        "id": sess.id,
        "profile_id": sess.profile_id,
        "application_id": sess.application_id,
        "page_restricted": sess.page_restricted,
        "created_at": sess.created_at,
        "items": [_item_dict(i) for i in items],
    }


async def parse_and_draft(ctx: WorkspaceContext, body: s.ParseBody) -> dict[str, Any]:
    await get_profile(ctx, body.profile_id)
    if body.application_id:
        app = await ctx.session.get(Application, body.application_id)
        if app is None or app.workspace_id != ctx.workspace_id:
            raise AppError("not_found", "Application not found", 404)

    page_hit = restr.detect_ai_restriction("", page_context=body.page_context or body.text[:2000])
    questions = splitter.split_questions(body.text)
    bundle = await _profile_bundle(ctx, body.profile_id)
    voice = bundle.get("voice") or {}

    bank_rows = list(
        (
            await ctx.session.execute(
                select(pm.AnswerBank).where(
                    pm.AnswerBank.profile_id == body.profile_id,
                    pm.AnswerBank.workspace_id == ctx.workspace_id,
                    pm.AnswerBank.approved.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )

    sess = AnswerDeskSession(
        workspace_id=ctx.workspace_id,
        profile_id=body.profile_id,
        application_id=body.application_id,
        source_text=body.text,
        page_restricted=page_hit.page_level or (page_hit.restricted and page_hit.page_level),
        created_by=ctx.user_id,
    )
    # page_restricted if page-level hit OR entire paste is restricted at page scope
    if page_hit.page_level:
        sess.page_restricted = True
    else:
        whole = restr.detect_ai_restriction(body.text[:1500], page_context=body.page_context)
        sess.page_restricted = whole.page_level

    ctx.session.add(sess)
    await ctx.session.flush()

    for i, q in enumerate(questions):
        q_hit = restr.detect_ai_restriction(q.text, page_context=body.page_context)
        ai_restricted = sess.page_restricted or q_hit.restricted
        item = AnswerDeskItem(
            workspace_id=ctx.workspace_id,
            session_id=sess.id,
            sort_order=i,
            question=q.text,
            constraints=q.constraints,
            ai_restricted=ai_restricted,
            legal_flag=q.legal_flag,
            char_limit=q.char_limit,
            format=q.format,
        )

        if ai_restricted:
            item.source = "restricted"
            item.draft = ""
            item.fact_notes = drafting.collect_fact_notes(bundle)
            item.evidence_refs = []
        elif restr.is_ai_use_disclosure_question(q.text):
            stance = (voice.get("ai_use_stance") or "").strip() or drafting.default_ai_stance()
            item.source = "ai_stance"
            item.draft = stance
            item.fact_notes = [{"id": "stance", "text": "Configured AI-use stance"}]
            item.evidence_refs = [{"id": "stance", "label": "AI-use stance"}]
        else:
            bank = matching.rank_bank_rows(q.text, bank_rows)
            # Prefer bank when canonical eligibility key also matches
            key = matching.match_canonical_key(q.text)
            bank_by_key = None
            if key:
                for row in bank_rows:
                    if row.key == key and (row.answer or "").strip():
                        bank_by_key = row
                        break
            if bank_by_key is not None:
                item.source = "bank"
                item.draft = bank_by_key.answer
                item.answer_bank_id = bank_by_key.id
                item.fact_notes = [
                    {"id": f"bank.{bank_by_key.key}", "text": "from your answer bank"}
                ]
                item.evidence_refs = [
                    {"id": f"bank.{bank_by_key.key}", "label": f"Answer bank · {bank_by_key.key}"}
                ]
            elif bank is not None and bank.answer.strip():
                item.source = "bank"
                item.draft = bank.answer
                item.answer_bank_id = bank.answer_id
                item.fact_notes = [{"id": f"bank.{bank.key}", "text": "from your answer bank"}]
                item.evidence_refs = [
                    {"id": f"bank.{bank.key}", "label": f"Answer bank · {bank.key}"}
                ]
            else:
                built = drafting.draft_answer(
                    question=q.text,
                    profile=bundle,
                    voice=voice,
                    char_limit=q.char_limit,
                    fmt=q.format,
                )
                item.source = built["source"]
                item.draft = built["draft"]
                item.fact_notes = built["fact_notes"]
                item.evidence_refs = built["evidence_refs"]
                item.banned_hits = built["banned_hits"]

        ctx.session.add(item)

    await audit.record(
        ctx,
        action="answer_desk.parsed",
        target_type="answer_desk_session",
        target_id=str(sess.id),
        after={"count": len(questions), "page_restricted": sess.page_restricted},
    )
    await ctx.session.flush()
    return await _session_read(ctx, sess.id)


async def get_session(ctx: WorkspaceContext, session_id: uuid.UUID) -> dict[str, Any]:
    return await _session_read(ctx, session_id)


async def redraft_item(ctx: WorkspaceContext, item_id: uuid.UUID, *, tone: str) -> dict[str, Any]:
    item = await ctx.session.get(AnswerDeskItem, item_id)
    if item is None or item.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Item not found", 404)
    if item.ai_restricted or item.source == "restricted":
        raise AppError("invalid_action", "Restricted questions have no draft", 422)
    if item.source == "bank":
        # Allow tone on bank answers only as a user edit path → becomes draft
        item.draft = drafting.apply_tone(item.draft, tone, char_limit=item.char_limit)
        item.source = "draft"
    else:
        sess = await ctx.session.get(AnswerDeskSession, item.session_id)
        assert sess is not None
        bundle = await _profile_bundle(ctx, sess.profile_id)
        built = drafting.draft_answer(
            question=item.question,
            profile=bundle,
            voice=bundle.get("voice"),
            tone=tone,
            char_limit=item.char_limit,
            fmt=item.format,
        )
        if built["source"] == "needs_story":
            item.source = "needs_story"
            item.draft = ""
            item.fact_notes = built["fact_notes"]
        else:
            item.draft = built["draft"]
            item.source = built["source"]
            item.fact_notes = built["fact_notes"]
            item.evidence_refs = built["evidence_refs"]
            item.banned_hits = built["banned_hits"]
    await ctx.session.flush()
    await ctx.session.refresh(item)
    return _item_dict(item)


async def patch_item(ctx: WorkspaceContext, item_id: uuid.UUID, draft: str) -> dict[str, Any]:
    item = await ctx.session.get(AnswerDeskItem, item_id)
    if item is None or item.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Item not found", 404)
    item.draft = draft
    if item.source == "restricted":
        item.source = "manual"
    elif item.source == "bank":
        item.source = "manual"
    await ctx.session.flush()
    return _item_dict(item)


async def save_to_bank(
    ctx: WorkspaceContext, item_id: uuid.UUID, *, key: str, approve: bool
) -> dict[str, Any]:
    item = await ctx.session.get(AnswerDeskItem, item_id)
    if item is None or item.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Item not found", 404)
    if not (item.draft or "").strip():
        raise AppError("validation_error", "Nothing to save", 422)
    sess = await ctx.session.get(AnswerDeskSession, item.session_id)
    assert sess is not None
    use_key = key if key != "custom_desk" else f"desk_{uuid.uuid4().hex[:10]}"
    created = await create_answer(
        ctx,
        sess.profile_id,
        ps.AnswerCreate(
            key=use_key,
            answer=item.draft,
            question_variants=[item.question[:500]],
            scope="global",
            approved=approve,
        ),
    )
    item.answer_bank_id = created.id
    await audit.record(
        ctx,
        action="answer_desk.saved_to_bank",
        target_type="answer_bank",
        target_id=str(created.id),
        after={"key": use_key},
    )
    await ctx.session.flush()
    out = _item_dict(item)
    out["answer_bank_id"] = item.answer_bank_id
    return out


async def list_for_application(ctx: WorkspaceContext, application_id: uuid.UUID) -> list[dict]:
    app = await ctx.session.get(Application, application_id)
    if app is None or app.workspace_id != ctx.workspace_id:
        raise AppError("not_found", "Application not found", 404)
    sessions = list(
        (
            await ctx.session.execute(
                select(AnswerDeskSession)
                .where(AnswerDeskSession.application_id == application_id)
                .order_by(AnswerDeskSession.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    out: list[dict[str, Any]] = []
    for sess in sessions:
        items = list(
            (
                await ctx.session.execute(
                    select(AnswerDeskItem)
                    .where(AnswerDeskItem.session_id == sess.id)
                    .order_by(AnswerDeskItem.sort_order.asc())
                )
            )
            .scalars()
            .all()
        )
        for it in items:
            d = _item_dict(it)
            d["session_id"] = sess.id
            out.append(d)
    return out


async def set_ai_stance(
    ctx: WorkspaceContext, profile_id: uuid.UUID, stance: str
) -> dict[str, str]:
    await get_profile(ctx, profile_id)
    voice = (
        await ctx.session.execute(
            select(pm.VoiceProfile).where(pm.VoiceProfile.profile_id == profile_id).limit(1)
        )
    ).scalar_one_or_none()
    if voice is None:
        voice = pm.VoiceProfile(
            workspace_id=ctx.workspace_id,
            profile_id=profile_id,
            ai_use_stance=stance.strip(),
            created_by=ctx.user_id,
        )
        ctx.session.add(voice)
    else:
        voice.ai_use_stance = stance.strip()
    await audit.record(
        ctx,
        action="answer_desk.stance_updated",
        target_type="voice_profile",
        target_id=str(voice.id) if voice.id else str(profile_id),
    )
    await ctx.session.flush()
    return {"ai_use_stance": voice.ai_use_stance}
