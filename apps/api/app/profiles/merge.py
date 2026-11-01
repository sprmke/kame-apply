"""Merge a parsed document draft into an existing Career Profile.

Preview classifies draft items as identical matches, field conflicts, or additions.
Resolve applies user choices in one transaction and marks the document confirmed.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.audit import service as audit
from app.core.errors import AppError
from app.core.security import WorkspaceContext
from app.profiles import models as m
from app.profiles import schemas as s
from app.profiles.documents import _get_document
from app.profiles.match import (
    NAME_MATCH,
    bullets_equivalent,
    json_safe,
    score_experience,
    score_named,
)
from app.profiles.parse import _load_draft
from app.profiles.parse_schema import (
    CertificationDraft,
    EducationDraft,
    ExperienceDraft,
    LanguageDraft,
    ProfileExtract,
    ProjectDraft,
    SkillDraft,
)
from app.profiles.service import _get_profile, evidence_strength

HEADER_FIELDS = ("display_name", "headline", "summary", "location", "timezone", "language")


def _field_diff(existing: Any, incoming: Any) -> dict[str, Any] | None:
    if existing is None and incoming is None:
        return None
    if json_safe(existing) == json_safe(incoming):
        return None
    # Filling a blank existing from incoming is an auto-merge, not a conflict.
    if existing is None and incoming is not None:
        return None
    if incoming is None:
        return None
    return {"existing": json_safe(existing), "incoming": json_safe(incoming)}


def _auto_fills(existing: Any, incoming: Any) -> Any | None:
    """Return incoming when existing is empty and incoming has a value."""
    if existing is None and incoming is not None:
        return incoming
    if existing == "" and incoming:
        return incoming
    return None


async def _existing_bullets(
    ctx: WorkspaceContext,
    *,
    experience_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
) -> list[m.Bullet]:
    q = select(m.Bullet).where(m.Bullet.profile_id.is_not(None))
    if experience_id is not None:
        q = select(m.Bullet).where(m.Bullet.experience_id == experience_id)
    elif project_id is not None:
        q = select(m.Bullet).where(m.Bullet.project_id == project_id)
    else:
        return []
    return list((await ctx.session.execute(q)).scalars())


def _bullet_additions(
    existing: list[m.Bullet], draft_bullets: list[Any], *, prefix: str
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, b in enumerate(draft_bullets):
        text = b.text if hasattr(b, "text") else b["text"]
        if any(bullets_equivalent(text, e.text) for e in existing):
            continue
        out.append(
            {
                "id": f"{prefix}:bullet:{i}",
                "draft_index": i,
                "text": text,
                "metrics": b.metrics if hasattr(b, "metrics") else b.get("metrics", []),
                "skills": b.skills if hasattr(b, "skills") else b.get("skills", []),
            }
        )
    return out


async def build_merge_preview(
    ctx: WorkspaceContext,
    profile_id: uuid.UUID,
    document_id: uuid.UUID,
    *,
    draft_override: dict[str, Any] | ProfileExtract | None = None,
) -> dict[str, Any]:
    await _get_profile(ctx, profile_id)
    doc = await _get_document(ctx, profile_id, document_id)
    quality = doc.parse_quality or {}
    if quality.get("confirmed_at"):
        raise AppError("document_already_confirmed", "This document was already confirmed", 409)
    if doc.status != "ready":
        raise AppError("document_not_ready", "Document is not ready", 422)
    draft = _load_draft(doc, draft_override)

    conflicts: list[dict[str, Any]] = []
    additions: list[dict[str, Any]] = []
    matches: list[dict[str, Any]] = []
    header_conflicts: list[dict[str, Any]] = []
    auto_header: dict[str, Any] = {}

    profile = await _get_profile(ctx, profile_id)
    for field in HEADER_FIELDS:
        existing = getattr(profile, field)
        incoming_field = getattr(draft, field)
        incoming = incoming_field.value if incoming_field else None
        diff = _field_diff(existing, incoming)
        if diff:
            header_conflicts.append({"id": f"header:{field}", "field": field, **diff})
        else:
            fill = _auto_fills(existing, incoming)
            if fill is not None:
                auto_header[field] = fill
    if draft.links:
        if profile.links and json_safe(profile.links) != json_safe(
            [{"label": lk.label, "url": lk.url} for lk in draft.links]
        ):
            header_conflicts.append(
                {
                    "id": "header:links",
                    "field": "links",
                    "existing": json_safe(profile.links),
                    "incoming": [{"label": lk.label, "url": lk.url} for lk in draft.links],
                }
            )
        elif not profile.links:
            auto_header["links"] = [{"label": lk.label, "url": lk.url} for lk in draft.links]

    # ---- experiences -------------------------------------------------------------------------
    existing_exps = list(
        (
            await ctx.session.execute(
                select(m.Experience).where(m.Experience.profile_id == profile_id)
            )
        ).scalars()
    )
    used_exp: set[uuid.UUID] = set()
    for di, exp in enumerate(draft.experiences):
        best: tuple[float, m.Experience, Any] | None = None
        for row in existing_exps:
            if row.id in used_exp:
                continue
            scored = score_experience(
                company_a=row.company,
                title_a=row.title,
                start_a=row.start_date,
                end_a=row.end_date,
                current_a=row.is_current,
                company_b=exp.company,
                title_b=exp.title,
                start_b=exp.start_date,
                end_b=exp.end_date,
                current_b=exp.is_current,
            )
            if scored.is_match and (best is None or scored.score > best[0]):
                best = (scored.score, row, scored)
        if best is None:
            additions.append(
                {
                    "id": f"experiences:new:{di}",
                    "section": "experiences",
                    "draft_index": di,
                    "label": f"{exp.company} — {exp.title}",
                    "incoming": exp.model_dump(mode="json"),
                }
            )
            continue
        score, row, scored = best
        used_exp.add(row.id)
        fields: dict[str, Any] = {}
        fills: dict[str, Any] = {}
        for fname, ex_v, in_v in (
            ("company", row.company, exp.company),
            ("title", row.title, exp.title),
            ("employment_type", row.employment_type, exp.employment_type),
            ("location", row.location, exp.location),
            ("start_date", row.start_date, exp.start_date),
            ("end_date", row.end_date, exp.end_date),
            ("is_current", row.is_current, exp.is_current),
            ("description", row.description, exp.description),
        ):
            # Never auto-fill an end date onto a still-current role; force a conflict instead.
            if fname == "end_date" and row.is_current and in_v is not None and ex_v is None:
                fields[fname] = {"existing": None, "incoming": json_safe(in_v)}
                continue
            diff = _field_diff(ex_v, in_v)
            if diff:
                fields[fname] = diff
            else:
                fill = _auto_fills(ex_v, in_v)
                if fill is not None:
                    fills[fname] = json_safe(fill)
        existing_b = await _existing_bullets(ctx, experience_id=row.id)
        bullet_adds = _bullet_additions(
            existing_b, exp.bullets, prefix=f"experiences:{row.id}:{di}"
        )
        entry = {
            "id": f"experiences:{row.id}:{di}",
            "section": "experiences",
            "existing_id": str(row.id),
            "draft_index": di,
            "label": f"{row.company} — {row.title}",
            "match_score": round(score, 3),
            "company_score": round(scored.company, 3),
            "title_score": round(scored.title, 3),
            "auto_fills": fills,
            "bullet_additions": bullet_adds,
        }
        if fields:
            conflicts.append({**entry, "fields": fields})
        else:
            matches.append(entry)

    # ---- projects ----------------------------------------------------------------------------
    existing_projects = list(
        (
            await ctx.session.execute(select(m.Project).where(m.Project.profile_id == profile_id))
        ).scalars()
    )
    used_proj: set[uuid.UUID] = set()
    for di, proj in enumerate(draft.projects):
        best_p: tuple[float, m.Project] | None = None
        for row in existing_projects:
            if row.id in used_proj:
                continue
            sc = score_named(row.name, proj.name)
            if sc >= NAME_MATCH and (best_p is None or sc > best_p[0]):
                best_p = (sc, row)
        if best_p is None:
            additions.append(
                {
                    "id": f"projects:new:{di}",
                    "section": "projects",
                    "draft_index": di,
                    "label": proj.name,
                    "incoming": proj.model_dump(mode="json"),
                }
            )
            continue
        score, row = best_p
        used_proj.add(row.id)
        fields = {}
        fills = {}
        for fname, ex_v, in_v in (
            ("name", row.name, proj.name),
            ("url", row.url, proj.url),
            ("description", row.description, proj.description),
            ("start_date", row.start_date, proj.start_date),
            ("end_date", row.end_date, proj.end_date),
        ):
            diff = _field_diff(ex_v, in_v)
            if diff:
                fields[fname] = diff
            else:
                fill = _auto_fills(ex_v, in_v)
                if fill is not None:
                    fills[fname] = json_safe(fill)
        existing_b = await _existing_bullets(ctx, project_id=row.id)
        bullet_adds = _bullet_additions(existing_b, proj.bullets, prefix=f"projects:{row.id}:{di}")
        entry = {
            "id": f"projects:{row.id}:{di}",
            "section": "projects",
            "existing_id": str(row.id),
            "draft_index": di,
            "label": row.name,
            "match_score": round(score, 3),
            "auto_fills": fills,
            "bullet_additions": bullet_adds,
        }
        if fields:
            conflicts.append({**entry, "fields": fields})
        else:
            matches.append(entry)

    # ---- education ---------------------------------------------------------------------------
    existing_edu = list(
        (
            await ctx.session.execute(
                select(m.Education).where(m.Education.profile_id == profile_id)
            )
        ).scalars()
    )
    used_edu: set[uuid.UUID] = set()
    for di, edu in enumerate(draft.education):
        best_e: tuple[float, m.Education] | None = None
        for row in existing_edu:
            if row.id in used_edu:
                continue
            inst = score_named(row.institution, edu.institution, org=True)
            deg = score_named(row.degree, edu.degree) if (row.degree or edu.degree) else 1.0
            sc = 0.7 * inst + 0.3 * deg
            if inst >= NAME_MATCH and sc >= 0.82 and (best_e is None or sc > best_e[0]):
                best_e = (sc, row)
        if best_e is None:
            additions.append(
                {
                    "id": f"education:new:{di}",
                    "section": "education",
                    "draft_index": di,
                    "label": edu.institution,
                    "incoming": edu.model_dump(mode="json"),
                }
            )
            continue
        score, row = best_e
        used_edu.add(row.id)
        fields = {}
        fills = {}
        for fname, ex_v, in_v in (
            ("institution", row.institution, edu.institution),
            ("degree", row.degree, edu.degree),
            ("field", row.field, edu.field),
            ("start_date", row.start_date, edu.start_date),
            ("end_date", row.end_date, edu.end_date),
            ("notes", row.notes, edu.notes),
        ):
            diff = _field_diff(ex_v, in_v)
            if diff:
                fields[fname] = diff
            else:
                fill = _auto_fills(ex_v, in_v)
                if fill is not None:
                    fills[fname] = json_safe(fill)
        entry = {
            "id": f"education:{row.id}:{di}",
            "section": "education",
            "existing_id": str(row.id),
            "draft_index": di,
            "label": row.institution,
            "match_score": round(score, 3),
            "auto_fills": fills,
            "bullet_additions": [],
        }
        if fields:
            conflicts.append({**entry, "fields": fields})
        else:
            matches.append(entry)

    # ---- certifications ----------------------------------------------------------------------
    existing_certs = list(
        (
            await ctx.session.execute(
                select(m.Certification).where(m.Certification.profile_id == profile_id)
            )
        ).scalars()
    )
    used_cert: set[uuid.UUID] = set()
    for di, cert in enumerate(draft.certifications):
        best_c: tuple[float, m.Certification] | None = None
        for row in existing_certs:
            if row.id in used_cert:
                continue
            sc = score_named(row.name, cert.name)
            if row.kind != cert.kind:
                continue
            if sc >= NAME_MATCH and (best_c is None or sc > best_c[0]):
                best_c = (sc, row)
        if best_c is None:
            additions.append(
                {
                    "id": f"certifications:new:{di}",
                    "section": "certifications",
                    "draft_index": di,
                    "label": cert.name,
                    "incoming": cert.model_dump(mode="json"),
                }
            )
            continue
        score, row = best_c
        used_cert.add(row.id)
        fields = {}
        fills = {}
        for fname, ex_v, in_v in (
            ("name", row.name, cert.name),
            ("issuer", row.issuer, cert.issuer),
            ("kind", row.kind, cert.kind),
            ("issued_on", row.issued_on, cert.issued_on),
            ("expires_on", row.expires_on, cert.expires_on),
            ("jurisdiction", row.jurisdiction, cert.jurisdiction),
        ):
            diff = _field_diff(ex_v, in_v)
            if diff:
                fields[fname] = diff
            else:
                fill = _auto_fills(ex_v, in_v)
                if fill is not None:
                    fills[fname] = json_safe(fill)
        entry = {
            "id": f"certifications:{row.id}:{di}",
            "section": "certifications",
            "existing_id": str(row.id),
            "draft_index": di,
            "label": row.name,
            "match_score": round(score, 3),
            "auto_fills": fills,
            "bullet_additions": [],
        }
        if fields:
            conflicts.append({**entry, "fields": fields})
        else:
            matches.append(entry)

    # ---- languages / skills (name match; level/proficiency conflicts) ------------------------
    existing_langs = list(
        (
            await ctx.session.execute(select(m.Language).where(m.Language.profile_id == profile_id))
        ).scalars()
    )
    used_lang: set[uuid.UUID] = set()
    for di, lang in enumerate(draft.languages):
        hit = next(
            (
                row
                for row in existing_langs
                if row.id not in used_lang and score_named(row.name, lang.name) >= NAME_MATCH
            ),
            None,
        )
        if hit is None:
            additions.append(
                {
                    "id": f"languages:new:{di}",
                    "section": "languages",
                    "draft_index": di,
                    "label": lang.name,
                    "incoming": lang.model_dump(mode="json"),
                }
            )
            continue
        used_lang.add(hit.id)
        fields = {}
        fills = {}
        diff = _field_diff(hit.proficiency, lang.proficiency)
        if diff:
            fields["proficiency"] = diff
        else:
            fill = _auto_fills(hit.proficiency, lang.proficiency)
            if fill is not None:
                fills["proficiency"] = fill
        entry = {
            "id": f"languages:{hit.id}:{di}",
            "section": "languages",
            "existing_id": str(hit.id),
            "draft_index": di,
            "label": hit.name,
            "match_score": 1.0,
            "auto_fills": fills,
            "bullet_additions": [],
        }
        if fields:
            conflicts.append({**entry, "fields": fields})
        else:
            matches.append(entry)

    existing_skills = list(
        (
            await ctx.session.execute(select(m.Skill).where(m.Skill.profile_id == profile_id))
        ).scalars()
    )
    used_skill: set[uuid.UUID] = set()
    for di, skill in enumerate(draft.skills):
        hit = next(
            (
                row
                for row in existing_skills
                if row.id not in used_skill and score_named(row.name, skill.name) >= NAME_MATCH
            ),
            None,
        )
        if hit is None:
            additions.append(
                {
                    "id": f"skills:new:{di}",
                    "section": "skills",
                    "draft_index": di,
                    "label": skill.name,
                    "incoming": skill.model_dump(mode="json"),
                }
            )
            continue
        used_skill.add(hit.id)
        fields = {}
        fills = {}
        for fname, ex_v, in_v in (
            ("level", hit.level, skill.level),
            ("years", hit.years, skill.years),
            ("last_used", hit.last_used, skill.last_used),
        ):
            diff = _field_diff(ex_v, in_v)
            if diff:
                fields[fname] = diff
            else:
                fill = _auto_fills(ex_v, in_v)
                if fill is not None:
                    fills[fname] = json_safe(fill)
        entry = {
            "id": f"skills:{hit.id}:{di}",
            "section": "skills",
            "existing_id": str(hit.id),
            "draft_index": di,
            "label": hit.name,
            "match_score": 1.0,
            "auto_fills": fills,
            "bullet_additions": [],
        }
        if fields:
            conflicts.append({**entry, "fields": fields})
        else:
            matches.append(entry)

    return {
        "document_id": document_id,
        "profile_id": profile_id,
        "header_conflicts": header_conflicts,
        "auto_header": auto_header,
        "conflicts": conflicts,
        "matches": matches,
        "additions": additions,
        "summary": {
            "conflicts": len(conflicts) + len(header_conflicts),
            "matches": len(matches),
            "additions": len(additions),
        },
    }


def _parse_date(value: Any) -> Any:
    if isinstance(value, str) and len(value) >= 8 and value[4] == "-":
        from datetime import date as date_cls

        return date_cls.fromisoformat(value[:10])
    return value


async def _add_bullets(
    ctx: WorkspaceContext,
    profile_id: uuid.UUID,
    bullets: list[Any],
    *,
    experience_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
) -> int:
    n = 0
    for b in bullets:
        text = b.text if hasattr(b, "text") else b["text"]
        metrics = b.metrics if hasattr(b, "metrics") else b.get("metrics", [])
        skills = b.skills if hasattr(b, "skills") else b.get("skills", [])
        ctx.session.add(
            m.Bullet(
                workspace_id=ctx.workspace_id,
                profile_id=profile_id,
                experience_id=experience_id,
                project_id=project_id,
                text=text,
                metrics=metrics,
                skills=skills,
                evidence_strength=evidence_strength(text, metrics),
                source="parsed",
            )
        )
        n += 1
    return n


async def resolve_merge(
    ctx: WorkspaceContext,
    profile_id: uuid.UUID,
    document_id: uuid.UUID,
    body: s.MergeResolve,
) -> dict[str, Any]:
    profile = await _get_profile(ctx, profile_id)
    doc = await _get_document(ctx, profile_id, document_id)
    quality = dict(doc.parse_quality or {})
    if quality.get("confirmed_at"):
        raise AppError("document_already_confirmed", "This document was already confirmed", 409)
    if doc.status != "ready":
        raise AppError("document_not_ready", "Document is not ready", 422)

    draft = _load_draft(doc, body.draft)
    preview = await build_merge_preview(ctx, profile_id, document_id, draft_override=draft)

    conflict_ids = {c["id"] for c in preview["conflicts"]}
    addition_ids = {a["id"] for a in preview["additions"]}
    match_by_id = {m_["id"]: m_ for m_ in preview["matches"]}
    conflict_by_id = {c["id"]: c for c in preview["conflicts"]}
    addition_by_id = {a["id"]: a for a in preview["additions"]}

    res_map = {r.id: r for r in body.resolutions}
    add_map = {a.id: a for a in body.additions}
    header_map = {h.field: h.action for h in body.header}

    # Every conflict must be resolved. Header conflicts use the `header` list.
    missing_conflicts = conflict_ids - set(res_map)
    missing_headers = {
        c["field"] for c in preview["header_conflicts"] if c["field"] not in header_map
    }
    if missing_conflicts or missing_headers:
        raise AppError(
            "unresolved_conflicts",
            "Resolve every conflict before merging",
            422,
            {
                "conflicts": sorted(missing_conflicts),
                "header_fields": sorted(missing_headers),
            },
        )

    # Additions default to add when omitted.
    for aid in addition_ids:
        if aid not in add_map:
            add_map[aid] = s.MergeAdditionAction(id=aid, action="add")

    stats = {
        "updated": 0,
        "created": 0,
        "bullets_added": 0,
        "skipped": 0,
        "header_fields": [],
    }

    # Header
    for hc in preview["header_conflicts"]:
        field = hc["field"]
        action = header_map[field]
        if action == "take_incoming":
            setattr(profile, field, hc["incoming"])
            stats["header_fields"].append(field)
        # keep_existing: no-op
    for field, value in preview["auto_header"].items():
        if field not in header_map or header_map.get(field) != "keep_existing":
            # auto-fill blanks unless user explicitly kept existing (N/A for blanks)
            if getattr(profile, field) in (None, "", []):
                setattr(profile, field, value)
                if field not in stats["header_fields"]:
                    stats["header_fields"].append(field)

    async def _apply_entity_update(
        entry: dict[str, Any], action: str, field_actions: dict[str, Any]
    ) -> None:
        section = entry["section"]
        existing_id = uuid.UUID(entry["existing_id"])
        draft_index = entry["draft_index"]
        model = {
            "experiences": m.Experience,
            "projects": m.Project,
            "education": m.Education,
            "certifications": m.Certification,
            "languages": m.Language,
            "skills": m.Skill,
        }[section]
        row = await ctx.session.get(model, existing_id)
        if row is None or row.profile_id != profile_id:  # type: ignore[attr-defined]
            raise AppError("item_not_found", "Matched profile entry not found", 404)

        incoming_obj: Any
        if section == "experiences":
            incoming_obj = draft.experiences[draft_index]
        elif section == "projects":
            incoming_obj = draft.projects[draft_index]
        elif section == "education":
            incoming_obj = draft.education[draft_index]
        elif section == "certifications":
            incoming_obj = draft.certifications[draft_index]
        elif section == "languages":
            incoming_obj = draft.languages[draft_index]
        else:
            incoming_obj = draft.skills[draft_index]

        fields = entry.get("fields") or {}
        changed = False
        # Always apply auto-fills.
        for fname, value in (entry.get("auto_fills") or {}).items():
            setattr(row, fname, _parse_date(value))
            changed = True

        if action == "keep_existing":
            pass
        elif action == "take_incoming":
            for fname in fields:
                setattr(row, fname, _parse_date(getattr(incoming_obj, fname)))
                changed = True
        elif action == "merge":
            for fname in fields:
                choice = field_actions.get(fname, "keep_existing")
                if choice == "take_incoming":
                    setattr(row, fname, _parse_date(getattr(incoming_obj, fname)))
                    changed = True
        else:
            raise AppError("invalid_resolution", "Unknown resolution action", 422)

        if section == "experiences" and getattr(row, "is_current", False):
            row.end_date = None
        if changed:
            stats["updated"] += 1

        # Bullet additions on matches/conflicts: default add unless listed under skip in body.bullet_actions
        bullet_skips = {b.id for b in body.bullet_actions if b.action == "skip"}
        for ba in entry.get("bullet_additions") or []:
            if ba["id"] in bullet_skips:
                stats["skipped"] += 1
                continue
            b = (
                draft.experiences[draft_index].bullets[ba["draft_index"]]
                if section == "experiences"
                else draft.projects[draft_index].bullets[ba["draft_index"]]
            )
            if section == "experiences":
                stats["bullets_added"] += await _add_bullets(
                    ctx, profile_id, [b], experience_id=existing_id
                )
            else:
                stats["bullets_added"] += await _add_bullets(
                    ctx, profile_id, [b], project_id=existing_id
                )

    # Resolve conflicts
    for cid, resolution in res_map.items():
        if cid not in conflict_by_id:
            raise AppError("unknown_conflict", f"Unknown conflict id: {cid}", 422)
        await _apply_entity_update(
            conflict_by_id[cid],
            resolution.action,
            resolution.field_actions,
        )

    # Matches: auto-fills + bullet additions only
    for entry in match_by_id.values():
        await _apply_entity_update(entry, "keep_existing", {})

    # Additions
    for aid, action in add_map.items():
        if aid not in addition_by_id:
            raise AppError("unknown_addition", f"Unknown addition id: {aid}", 422)
        if action.action == "skip":
            stats["skipped"] += 1
            continue
        add = addition_by_id[aid]
        section = add["section"]
        di = add["draft_index"]
        if section == "experiences":
            exp: ExperienceDraft = draft.experiences[di]
            row_exp = m.Experience(
                workspace_id=ctx.workspace_id,
                profile_id=profile_id,
                company=exp.company,
                title=exp.title,
                employment_type=exp.employment_type,
                location=exp.location,
                start_date=exp.start_date,
                end_date=exp.end_date,
                is_current=exp.is_current,
                description=exp.description,
                source="parsed",
            )
            ctx.session.add(row_exp)
            await ctx.session.flush()
            stats["created"] += 1
            stats["bullets_added"] += await _add_bullets(
                ctx, profile_id, exp.bullets, experience_id=row_exp.id
            )
        elif section == "projects":
            proj: ProjectDraft = draft.projects[di]
            row_proj = m.Project(
                workspace_id=ctx.workspace_id,
                profile_id=profile_id,
                name=proj.name,
                url=proj.url,
                description=proj.description,
                start_date=proj.start_date,
                end_date=proj.end_date,
                source="parsed",
            )
            ctx.session.add(row_proj)
            await ctx.session.flush()
            stats["created"] += 1
            stats["bullets_added"] += await _add_bullets(
                ctx, profile_id, proj.bullets, project_id=row_proj.id
            )
        elif section == "education":
            edu: EducationDraft = draft.education[di]
            ctx.session.add(
                m.Education(
                    workspace_id=ctx.workspace_id,
                    profile_id=profile_id,
                    institution=edu.institution,
                    degree=edu.degree,
                    field=edu.field,
                    start_date=edu.start_date,
                    end_date=edu.end_date,
                    notes=edu.notes,
                    source="parsed",
                )
            )
            stats["created"] += 1
        elif section == "certifications":
            cert: CertificationDraft = draft.certifications[di]
            ctx.session.add(
                m.Certification(
                    workspace_id=ctx.workspace_id,
                    profile_id=profile_id,
                    name=cert.name,
                    issuer=cert.issuer,
                    kind=cert.kind,
                    issued_on=cert.issued_on,
                    expires_on=cert.expires_on,
                    jurisdiction=cert.jurisdiction,
                    source="parsed",
                )
            )
            stats["created"] += 1
        elif section == "languages":
            lang: LanguageDraft = draft.languages[di]
            ctx.session.add(
                m.Language(
                    workspace_id=ctx.workspace_id,
                    profile_id=profile_id,
                    name=lang.name,
                    proficiency=lang.proficiency,
                    source="parsed",
                )
            )
            stats["created"] += 1
        elif section == "skills":
            skill: SkillDraft = draft.skills[di]
            ctx.session.add(
                m.Skill(
                    workspace_id=ctx.workspace_id,
                    profile_id=profile_id,
                    name=skill.name,
                    level=skill.level,
                    years=skill.years,
                    last_used=skill.last_used,
                    source="parsed",
                )
            )
            stats["created"] += 1

    doc.parsed = draft.model_dump(mode="json")
    quality["confirmed_at"] = datetime.now(UTC).isoformat()
    quality["merged"] = True
    quality["low_confidence_paths"] = draft.low_confidence_paths()
    quality["low_confidence_count"] = len(quality["low_confidence_paths"])
    doc.parse_quality = quality
    await ctx.session.flush()

    await audit.record(
        ctx,
        action="document.merged",
        target_type="document",
        target_id=str(document_id),
        after={
            "profile_id": str(profile_id),
            "stats": stats,
            "conflict_count": len(conflict_ids),
            "addition_count": len(addition_ids),
        },
    )
    if stats["header_fields"]:
        await audit.record(
            ctx,
            action="profile.updated",
            target_type="profile",
            target_id=str(profile_id),
            after={"fields": stats["header_fields"], "from_document": str(document_id)},
        )

    return {
        "document_id": document_id,
        "profile_id": profile_id,
        "stats": stats,
    }
