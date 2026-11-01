"""Find weak spots in a Career Profile for the interview drawer.

Deterministic: no LLM. One question at a time, strongest gaps first.
"""

from __future__ import annotations

import itertools
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from sqlalchemy import select

from app.core.security import WorkspaceContext
from app.profiles import models as m
from app.profiles.service import _get_profile

GapKind = Literal["bullet_metric", "bullet_text", "skill_years", "gap_note"]
TargetType = Literal["bullet", "skill", "experience"]


@dataclass(frozen=True, slots=True)
class Gap:
    id: str
    kind: GapKind
    target_type: TargetType
    target_id: uuid.UUID
    question: str
    context: dict[str, Any]


def _clip(text: str, n: int = 160) -> str:
    t = " ".join(text.split())
    return t if len(t) <= n else t[: n - 1] + "…"


async def find_gaps(ctx: WorkspaceContext, profile_id: uuid.UUID) -> list[Gap]:
    await _get_profile(ctx, profile_id)
    gaps: list[Gap] = []

    bullets = list(
        (
            await ctx.session.execute(
                select(m.Bullet)
                .where(m.Bullet.profile_id == profile_id, m.Bullet.do_not_use.is_(False))
                .order_by(m.Bullet.sort_order, m.Bullet.created_at)
            )
        ).scalars()
    )
    for b in bullets:
        metrics = b.metrics or []
        if b.evidence_strength == "weak" or not metrics:
            gaps.append(
                Gap(
                    id=f"bullet_metric:{b.id}",
                    kind="bullet_metric",
                    target_type="bullet",
                    target_id=b.id,
                    question=(
                        f'You wrote: "{_clip(b.text)}". '
                        "What measurable outcome, scale, or scope can you add "
                        "(numbers, %, time saved, people, systems)?"
                    ),
                    context={"text": b.text, "evidence_strength": b.evidence_strength},
                )
            )

    skills = list(
        (
            await ctx.session.execute(
                select(m.Skill)
                .where(m.Skill.profile_id == profile_id, m.Skill.do_not_use.is_(False))
                .order_by(m.Skill.sort_order, m.Skill.created_at)
            )
        ).scalars()
    )
    for sk in skills:
        if sk.years is None and not (sk.evidence_refs or []):
            gaps.append(
                Gap(
                    id=f"skill_years:{sk.id}",
                    kind="skill_years",
                    target_type="skill",
                    target_id=sk.id,
                    question=(
                        f'How many years have you used "{sk.name}", '
                        "and where did you use it most recently?"
                    ),
                    context={"name": sk.name},
                )
            )

    experiences = list(
        (
            await ctx.session.execute(
                select(m.Experience)
                .where(m.Experience.profile_id == profile_id, m.Experience.do_not_use.is_(False))
                .order_by(m.Experience.start_date.nulls_last(), m.Experience.created_at)
            )
        ).scalars()
    )
    dated = [
        e
        for e in experiences
        if e.start_date is not None and (e.end_date is not None or e.is_current)
    ]
    dated.sort(key=lambda e: e.start_date or date.min)
    for prev, curr in itertools.pairwise(dated):
        prev_end = prev.end_date
        curr_start = curr.start_date
        if prev_end and curr_start and (curr_start - prev_end).days > 120:
            months = (curr_start - prev_end).days // 30
            gaps.append(
                Gap(
                    id=f"gap_note:{prev.id}:{curr.id}",
                    kind="gap_note",
                    target_type="experience",
                    target_id=curr.id,
                    question=(
                        f"There are about {months} months between "
                        f"{prev.company} and {curr.company}. "
                        "What were you doing then (study, care, travel, contract, other)?"
                    ),
                    context={
                        "from_company": prev.company,
                        "to_company": curr.company,
                        "months": months,
                    },
                )
            )

    return gaps
