"""Deterministic LinkedIn copy suggestions from Career Profile + Track (truthful only)."""

from __future__ import annotations

from typing import Any

from app.strategy.schemas import LinkedInOptimizeRead, SuggestionBlock

_HEADLINE_MAX = 220
_ABOUT_MAX = 2600


def _titles_from_criteria(structured: dict[str, Any]) -> list[str]:
    titles: list[str] = []
    for t in structured.get("titles") or []:
        if isinstance(t, dict) and t.get("title") and not t.get("exclude"):
            titles.append(str(t["title"]).strip())
        elif isinstance(t, str) and t.strip():
            titles.append(t.strip())
    return titles[:5]


def _locations_from_criteria(structured: dict[str, Any]) -> list[str]:
    locs: list[str] = []
    for loc in structured.get("locations") or []:
        if isinstance(loc, dict):
            label = loc.get("label") or loc.get("city") or loc.get("country")
            if label:
                locs.append(str(label))
        elif isinstance(loc, str):
            locs.append(loc)
    remote = structured.get("remote") or structured.get("work_modes") or []
    if "remote" in remote or (isinstance(remote, dict) and remote.get("anywhere")):
        locs.append("Remote")
    return locs[:5]


def _skills_ordered(
    profile_skills: list[str], track_must: list[str], track_nice: list[str]
) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for pool in (track_must, track_nice, profile_skills):
        for s in pool:
            key = s.strip().lower()
            if not key or key in seen:
                continue
            # Only keep skills the profile actually has (truthful)
            if pool is track_must or pool is track_nice:
                if not any(s.strip().lower() == p.strip().lower() for p in profile_skills):
                    continue
            seen.add(key)
            out.append(s.strip())
    return out[:20]


def build_suggestions(
    *,
    track_id,
    track_name: str,
    structured: dict[str, Any],
    display_name: str,
    headline: str | None,
    summary: str | None,
    location: str | None,
    experiences: list[dict[str, Any]],
    skills: list[str],
) -> LinkedInOptimizeRead:
    titles = _titles_from_criteria(structured) or (
        [track_name] if track_name else ["Software Engineer"]
    )
    target = titles[0]
    skill_sets = structured.get("skills") or {}
    must = list(skill_sets.get("must") or [])
    nice = list(skill_sets.get("nice") or [])
    ordered = _skills_ordered(skills, must, nice)

    # Headline: current title + target alignment, ≤ 220
    current_title = ""
    current_co = ""
    if experiences:
        current_title = str(experiences[0].get("title") or "")
        current_co = str(experiences[0].get("company") or "")
    parts = []
    if current_title:
        if target.lower() not in current_title.lower():
            parts.append(f"{current_title} | open to {target}")
        else:
            parts.append(current_title)
    else:
        parts.append(target)
    if ordered[:3]:
        parts.append(" · ".join(ordered[:3]))
    if location:
        parts.append(location)
    hl = " | ".join(parts)
    if len(hl) > _HEADLINE_MAX:
        hl = hl[: _HEADLINE_MAX - 1].rstrip() + "…"
    headline_block = SuggestionBlock(
        kind="headline",
        text=hl,
        why="Uses your real title and Track target titles; skills only from your profile.",
        char_count=len(hl),
    )

    about_bits = []
    if summary:
        about_bits.append(summary.strip())
    else:
        about_bits.append(
            f"{display_name or 'I'} work as {current_title or target}"
            + (f" at {current_co}" if current_co else "")
            + f". Targeting {', '.join(titles)}."
        )
    if ordered:
        about_bits.append("Skills: " + ", ".join(ordered[:12]) + ".")
    about_bits.append("Open to roles that match my Track criteria. Happy to connect.")
    about = "\n\n".join(about_bits)
    if len(about) > _ABOUT_MAX:
        about = about[: _ABOUT_MAX - 1] + "…"
    about_block = SuggestionBlock(
        kind="about",
        text=about,
        why="Built only from Career Profile summary, titles, and skills you already have.",
        char_count=len(about),
    )

    exp_blocks: list[SuggestionBlock] = []
    for ex in experiences[:5]:
        title = str(ex.get("title") or "")
        company = str(ex.get("company") or "")
        desc = str(ex.get("description") or "").strip()
        # Suggest title alignment only when target is a synonym-ish add-on, never rewrite history
        suggested_title = title
        why = "Keep your official title; do not invent roles."
        if title and target and target.lower() not in title.lower():
            suggested_title = f"{title} (focus: {target})"
            why = (
                "Keeps your official title and adds Track focus in parentheses. "
                "Only paste if that focus is true for the role."
            )
        body = desc
        if not body and ordered:
            body = f"Worked with {', '.join(ordered[:5])}."
        text = f"{suggested_title} · {company}\n{body}".strip()
        exp_blocks.append(
            SuggestionBlock(
                kind="experience",
                text=text,
                why=why,
                char_count=len(text),
            )
        )

    locs = _locations_from_criteria(structured)
    if location and location not in locs:
        locs = [location, *locs]
    open_to_work = [
        "Turn on Open to work → Recruiters only (not all LinkedIn).",
        f"Job titles: {', '.join(titles)}",
        f"Locations: {', '.join(locs) if locs else (location or 'your current city')}",
        "Start date: flexible / as available",
        "Job types matching your Track employment types",
    ]

    github = [
        "Pin 2-3 repos that match Track must-have skills",
        "README: what it is, how to run, one screenshot or sample output",
        "Remove empty or unfinished repos from the top of your profile",
        "Link the same GitHub URL in Career Profile links",
    ]

    return LinkedInOptimizeRead(
        track_id=track_id,
        headline=headline_block,
        about=about_block,
        skills_order=ordered,
        skills_why="Must-have Track skills you already have first, then nice-to-haves, then the rest.",
        experience=exp_blocks,
        open_to_work=open_to_work,
        github_checklist=github,
    )
