"""Title and skill normalizers (trigram + aliases; LLM tiebreak optional)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import WorkspaceContext
from app.profiles import models as profile_models
from app.taxonomy import models as m
from app.taxonomy.aliases import SKILL_ALIASES, canonicalize_skill


@dataclass(frozen=True)
class OccupationCandidate:
    id: uuid.UUID
    scheme: str
    code: str
    label: str
    score: float


@dataclass(frozen=True)
class SkillMatch:
    raw: str
    canonical: str
    skill_id: uuid.UUID | None
    score: float
    source: str  # alias | taxonomy | passthrough


async def normalize_title(
    session: AsyncSession, title: str, *, limit: int = 8
) -> list[OccupationCandidate]:
    q = title.strip()
    if not q:
        return []
    # pg_trgm similarity against label and alt_titles text
    rows = (
        (
            await session.execute(
                text(
                    """
                SELECT id, scheme, code, label,
                       GREATEST(
                         similarity(label, :q),
                         COALESCE((
                           SELECT MAX(similarity(a, :q))
                           FROM jsonb_array_elements_text(alt_titles) AS t(a)
                         ), 0)
                       ) AS score
                FROM taxonomy_occupations
                WHERE label % :q
                   OR EXISTS (
                     SELECT 1 FROM jsonb_array_elements_text(alt_titles) AS t(a)
                     WHERE a % :q
                   )
                ORDER BY score DESC
                LIMIT :lim
                """
                ),
                {"q": q, "lim": limit},
            )
        )
        .mappings()
        .all()
    )
    return [
        OccupationCandidate(
            id=r["id"],
            scheme=r["scheme"],
            code=r["code"],
            label=r["label"],
            score=float(r["score"] or 0),
        )
        for r in rows
    ]


async def normalize_skill(session: AsyncSession, raw: str) -> SkillMatch:
    canonical = canonicalize_skill(raw)
    key = canonical.casefold()
    # DB alias first
    alias = (
        await session.execute(
            select(m.TaxonomyAlias).where(
                m.TaxonomyAlias.kind == "skill",
                m.TaxonomyAlias.alias_key == raw.strip().casefold(),
            )
        )
    ).scalar_one_or_none()
    if alias is not None:
        return SkillMatch(
            raw=raw,
            canonical=alias.canonical,
            skill_id=alias.skill_id,
            score=1.0,
            source="alias",
        )
    if raw.strip().casefold() in SKILL_ALIASES:
        # Resolve taxonomy row by label when present
        skill = (
            await session.execute(
                select(m.TaxonomySkill).where(func.lower(m.TaxonomySkill.label) == key).limit(1)
            )
        ).scalar_one_or_none()
        return SkillMatch(
            raw=raw,
            canonical=canonical,
            skill_id=skill.id if skill else None,
            score=0.95,
            source="alias",
        )
    row = (
        (
            await session.execute(
                text(
                    """
                SELECT id, label, similarity(label, :q) AS score
                FROM taxonomy_skills
                WHERE label % :q
                ORDER BY score DESC
                LIMIT 1
                """
                ),
                {"q": canonical},
            )
        )
        .mappings()
        .first()
    )
    if row and float(row["score"] or 0) >= 0.4:
        return SkillMatch(
            raw=raw,
            canonical=row["label"],
            skill_id=row["id"],
            score=float(row["score"]),
            source="taxonomy",
        )
    return SkillMatch(raw=raw, canonical=canonical, skill_id=None, score=0.0, source="passthrough")


async def suggest_adjacent_titles(
    session: AsyncSession, occupation_id: uuid.UUID, *, limit: int = 10
) -> list[str]:
    occ = await session.get(m.TaxonomyOccupation, occupation_id)
    if occ is None:
        return []
    alts = [str(a) for a in (occ.alt_titles or [])][:limit]
    if len(alts) >= limit:
        return alts
    # Same ISCO family if present
    if occ.isco_code:
        peers = (
            (
                await session.execute(
                    select(m.TaxonomyOccupation.label)
                    .where(
                        m.TaxonomyOccupation.isco_code == occ.isco_code,
                        m.TaxonomyOccupation.id != occ.id,
                    )
                    .limit(limit - len(alts))
                )
            )
            .scalars()
            .all()
        )
        for label in peers:
            if label not in alts:
                alts.append(label)
    return alts[:limit]


async def backfill_profile_skills(ctx: WorkspaceContext, profile_id: uuid.UUID) -> dict[str, Any]:
    """Map raw profile_skills.name → taxonomy skill_id where possible."""
    rows = list(
        (
            await ctx.session.execute(
                select(profile_models.Skill).where(profile_models.Skill.profile_id == profile_id)
            )
        ).scalars()
    )
    linked = 0
    for skill in rows:
        if skill.skill_id is not None:
            continue
        match = await normalize_skill(ctx.session, skill.name)
        if match.skill_id is not None:
            skill.skill_id = match.skill_id
            if match.canonical and match.canonical != skill.name:
                skill.name = match.canonical
            linked += 1
    await ctx.session.flush()
    return {"profile_id": str(profile_id), "linked": linked, "total": len(rows)}
