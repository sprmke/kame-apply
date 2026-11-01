"""Profile interview: gap questions → proposals → accept into profile facts.

Questions are deterministic templates (gaps.py). User answers become proposals; nothing is
written to fact tables until accept. Audit never stores question/answer text.
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import AsyncIterator
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.profiles import models as m
from app.profiles import schemas as s
from app.profiles.gaps import Gap, find_gaps
from app.profiles.sanitize import strip_sensitive_numbers
from app.profiles.service import _get_profile, evidence_strength

_NUMBER = re.compile(
    r"(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>%|percent|people|nurses|beds|patients|"
    r"services|systems|months|years|hrs?|hours|days|weeks|\$|usd|php|sgd)?",
    re.I,
)


def _reject_sensitive(text: str) -> None:
    _, kinds = strip_sensitive_numbers(text)
    if kinds:
        raise AppError(
            "sensitive_content",
            "Remove government IDs and card numbers from answers",
            422,
            {"kinds": list(kinds)},
        )


def _extract_metrics(answer: str) -> list[dict[str, str]]:
    metrics: list[dict[str, str]] = []
    seen: set[str] = set()
    for match in _NUMBER.finditer(answer):
        val = match.group("val")
        unit = (match.group("unit") or "").lower()
        if unit in ("percent",):
            unit = "%"
        name = unit or "value"
        key = f"{name}:{val}"
        if key in seen:
            continue
        seen.add(key)
        change = f"{val}{unit}" if unit and unit != "value" else val
        metrics.append({"name": name[:40], "change": change[:40]})
        if len(metrics) >= 5:
            break
    return metrics


def _years_from_answer(answer: str) -> Decimal | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:years?|yrs?)", answer, re.I)
    if not m:
        m = re.search(r"\b(\d+(?:\.\d+)?)\b", answer)
    if not m:
        return None
    try:
        return Decimal(m.group(1)).quantize(Decimal("0.1"))
    except Exception:
        return None


async def _gap_by_id(ctx: WorkspaceContext, profile_id: uuid.UUID, gap_id: str) -> Gap:
    for gap in await find_gaps(ctx, profile_id):
        if gap.id == gap_id:
            return gap
    raise AppError("gap_not_found", "That follow-up is no longer available", 404)


def _build_payload(gap: Gap, answer: str) -> dict[str, Any]:
    if gap.kind == "bullet_metric":
        metrics = _extract_metrics(answer)
        # Keep original bullet text; metrics attach from the answer.
        return {
            "metrics": metrics or [{"name": "detail", "change": answer.strip()[:80]}],
            "note": answer.strip()[:500],
            "evidence_strength": "strong" if metrics else "ok",
        }
    if gap.kind == "skill_years":
        years = _years_from_answer(answer)
        return {"years": float(years) if years is not None else None, "note": answer.strip()[:500]}
    if gap.kind == "gap_note":
        return {"note": answer.strip()[:1000], "months": gap.context.get("months")}
    return {"note": answer.strip()[:500]}


async def list_gaps(ctx: WorkspaceContext, profile_id: uuid.UUID) -> list[s.InterviewGapRead]:
    gaps = await find_gaps(ctx, profile_id)
    return [
        s.InterviewGapRead(
            id=g.id,
            kind=g.kind,
            target_type=g.target_type,
            target_id=g.target_id,
            question=g.question,
            context=g.context,
        )
        for g in gaps
    ]


async def next_gap(ctx: WorkspaceContext, profile_id: uuid.UUID) -> s.InterviewGapRead | None:
    gaps = await list_gaps(ctx, profile_id)
    return gaps[0] if gaps else None


async def create_turn(
    ctx: WorkspaceContext, profile_id: uuid.UUID, body: s.InterviewTurn
) -> s.InterviewTurnRead:
    await _get_profile(ctx, profile_id)
    _reject_sensitive(body.answer)
    gap = await _gap_by_id(ctx, profile_id, body.gap_id)
    payload = _build_payload(gap, body.answer.strip())
    row = m.ProfileProposal(
        workspace_id=ctx.workspace_id,
        profile_id=profile_id,
        kind=gap.kind,
        target_type=gap.target_type,
        target_id=gap.target_id,
        question=gap.question,
        user_answer=body.answer.strip(),
        payload=payload,
        status="pending",
        created_by=ctx.user_id,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await audit.record(
        ctx,
        action="interview.proposal_created",
        target_type="proposal",
        target_id=str(row.id),
        after={
            "profile_id": str(profile_id),
            "kind": row.kind,
            "target_type": row.target_type,
            "target_id": str(row.target_id),
        },
    )
    nxt = await next_gap(ctx, profile_id)
    # Skip the same gap id if still listed (pending proposal doesn't remove the gap until accept).
    if nxt and nxt.id == gap.id:
        remaining = [g for g in await list_gaps(ctx, profile_id) if g.id != gap.id]
        nxt = remaining[0] if remaining else None
    return s.InterviewTurnRead(
        proposal=_proposal_read(row),
        next_gap=nxt,
    )


def _proposal_read(row: m.ProfileProposal) -> s.ProposalRead:
    return s.ProposalRead(
        id=row.id,
        profile_id=row.profile_id,
        kind=row.kind,  # type: ignore[arg-type]
        target_type=row.target_type,  # type: ignore[arg-type]
        target_id=row.target_id,
        question=row.question,
        payload=row.payload or {},
        status=row.status,  # type: ignore[arg-type]
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def list_proposals(
    ctx: WorkspaceContext, profile_id: uuid.UUID, *, status: str | None = "pending"
) -> list[s.ProposalRead]:
    await _get_profile(ctx, profile_id)
    q = select(m.ProfileProposal).where(m.ProfileProposal.profile_id == profile_id)
    if status:
        q = q.where(m.ProfileProposal.status == status)
    q = q.order_by(m.ProfileProposal.created_at.desc())
    rows = list((await ctx.session.execute(q)).scalars())
    return [_proposal_read(r) for r in rows]


async def _get_proposal(
    ctx: WorkspaceContext, profile_id: uuid.UUID, proposal_id: uuid.UUID
) -> m.ProfileProposal:
    await _get_profile(ctx, profile_id)
    row = await ctx.session.get(m.ProfileProposal, proposal_id)
    if row is None or row.profile_id != profile_id or row.workspace_id != ctx.workspace_id:
        raise AppError("proposal_not_found", "Proposal not found", 404)
    return row


async def accept_proposal(
    ctx: WorkspaceContext, profile_id: uuid.UUID, proposal_id: uuid.UUID
) -> s.ProposalRead:
    row = await _get_proposal(ctx, profile_id, proposal_id)
    if row.status != "pending":
        raise AppError("proposal_not_pending", "Proposal is no longer pending", 409)
    payload = row.payload or {}

    if row.kind == "bullet_metric" and row.target_type == "bullet":
        bullet = await ctx.session.get(m.Bullet, row.target_id)
        if bullet is None or bullet.profile_id != profile_id:
            raise AppError("target_not_found", "Bullet not found", 404)
        metrics = list(bullet.metrics or [])
        for item in payload.get("metrics") or []:
            if item not in metrics:
                metrics.append(item)
        bullet.metrics = metrics
        bullet.source = "interview"
        bullet.evidence_strength = evidence_strength(bullet.text, metrics)
    elif row.kind == "skill_years" and row.target_type == "skill":
        skill = await ctx.session.get(m.Skill, row.target_id)
        if skill is None or skill.profile_id != profile_id:
            raise AppError("target_not_found", "Skill not found", 404)
        years = payload.get("years")
        if years is not None:
            skill.years = Decimal(str(years))
        skill.source = "interview"
    elif row.kind == "gap_note" and row.target_type == "experience":
        exp = await ctx.session.get(m.Experience, row.target_id)
        if exp is None or exp.profile_id != profile_id:
            raise AppError("target_not_found", "Experience not found", 404)
        note = str(payload.get("note") or "").strip()
        if note:
            existing = (exp.description or "").rstrip()
            addition = f"Career note: {note}"
            exp.description = f"{existing}\n\n{addition}".strip() if existing else addition
            exp.source = "interview"
    else:
        raise AppError("unsupported_proposal", "Cannot apply this proposal kind", 422)

    row.status = "accepted"
    await ctx.session.flush()
    await ctx.session.refresh(row)
    await audit.record(
        ctx,
        action="interview.proposal_accepted",
        target_type="proposal",
        target_id=str(row.id),
        after={
            "profile_id": str(profile_id),
            "kind": row.kind,
            "target_type": row.target_type,
            "target_id": str(row.target_id),
        },
    )
    return _proposal_read(row)


async def reject_proposal(
    ctx: WorkspaceContext, profile_id: uuid.UUID, proposal_id: uuid.UUID
) -> s.ProposalRead:
    row = await _get_proposal(ctx, profile_id, proposal_id)
    if row.status != "pending":
        raise AppError("proposal_not_pending", "Proposal is no longer pending", 409)
    row.status = "rejected"
    await ctx.session.flush()
    await ctx.session.refresh(row)
    await audit.record(
        ctx,
        action="interview.proposal_rejected",
        target_type="proposal",
        target_id=str(row.id),
        after={
            "profile_id": str(profile_id),
            "kind": row.kind,
            "target_id": str(row.target_id),
        },
    )
    return _proposal_read(row)


async def prepare_question_stream(ctx: WorkspaceContext, profile_id: uuid.UUID) -> list[bytes]:
    """Load the next gap while the request session is open, then return SSE frames."""
    gap = await next_gap(ctx, profile_id)
    frames: list[bytes] = []
    if gap is None:
        frames.append(_sse("done", {"ok": True, "remaining": 0}))
        return frames
    frames.append(
        _sse(
            "gap",
            {
                "id": gap.id,
                "kind": gap.kind,
                "target_type": gap.target_type,
                "target_id": str(gap.target_id),
                "context": gap.context,
            },
        )
    )
    text = gap.question
    step = 24
    for i in range(0, len(text), step):
        frames.append(_sse("token", {"text": text[i : i + step]}))
    frames.append(_sse("done", {"ok": True, "remaining": 1, "gap_id": gap.id}))
    return frames


async def iter_frames(frames: list[bytes]) -> AsyncIterator[bytes]:
    for frame in frames:
        yield frame


def _sse(event: str, data: dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n".encode()
