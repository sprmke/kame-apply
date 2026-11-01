"""Stage 2 rule score components (0-100 each) and weighted blend."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.jobs.normalize import normalize_title
from app.tracks.criteria import CriteriaV1, criteria_from_dict

DEFAULT_WEIGHTS: dict[str, float] = {
    "title": 0.22,
    "skills": 0.28,
    "seniority": 0.12,
    "salary": 0.12,
    "freshness": 0.08,
    "location": 0.10,
    "semantic": 0.08,
    "llm": 0.00,  # filled when AI fit runs
}


def clamp_weights(weights: dict[str, float]) -> dict[str, float]:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    # Bound learning drift
    for k, v in list(w.items()):
        w[k] = max(0.02, min(0.5, float(v)))
    s = sum(w.values()) or 1.0
    return {k: v / s for k, v in w.items()}


def rule_components(
    job: dict[str, Any],
    structured: dict[str, Any] | CriteriaV1,
    *,
    profile_skills: list[str] | None = None,
    profile_seniority: str | None = None,
) -> tuple[dict[str, float], list[str]]:
    c = structured if isinstance(structured, CriteriaV1) else criteria_from_dict(structured)
    comps: dict[str, float] = {}
    reasons: list[str] = []

    # Title
    title_blob = f"{job.get('title', '')} {job.get('normalized_title', '')}".lower()
    norm = job.get("normalized_title") or normalize_title(job.get("title") or "")
    title_score = 40.0
    if c.titles:
        best = 0.0
        for t in c.titles:
            if t.exclude:
                continue
            nt = normalize_title(t.title)
            if nt == norm or t.title.lower() == (job.get("title") or "").lower():
                best = 100.0
            elif nt in norm or t.title.lower() in title_blob:
                best = max(best, 85.0)
            else:
                tokens = {w for w in norm.split() if len(w) > 2}
                want = {w for w in nt.split() if len(w) > 2}
                if tokens & want:
                    best = max(best, 65.0)
        title_score = best or 25.0
        if title_score >= 85:
            reasons.append("Title match")
    comps["title"] = title_score

    # Skills
    must = list(c.skills.must) if c.skills else []
    nice = list(c.skills.nice) if c.skills else []
    blob = f"{job.get('description_text', '')} {' '.join(job.get('skills') or [])}".lower()
    profile_set = {s.lower() for s in (profile_skills or [])}
    if must:
        hit = sum(1 for sk in must if sk.lower() in blob)
        cov = hit / len(must)
        comps["skills"] = round(100.0 * cov, 2)
        # Bonus if profile also has them
        overlap = sum(1 for sk in must if sk.lower() in profile_set)
        if overlap:
            comps["skills"] = min(100.0, comps["skills"] + 5 * overlap)
            reasons.append(f"{overlap}/{len(must)} must-skills evidenced")
        elif hit:
            reasons.append(f"{hit}/{len(must)} must-skills in posting")
    else:
        comps["skills"] = 70.0
    if nice:
        nice_hit = sum(1 for sk in nice if sk.lower() in blob)
        if nice_hit:
            comps["skills"] = min(100.0, comps["skills"] + 3 * nice_hit)

    # Seniority
    job_sen = (job.get("seniority") or "").lower()
    want_sen = [s.lower() for s in (c.seniority or [])]
    if want_sen and job_sen:
        comps["seniority"] = 100.0 if job_sen in want_sen else 35.0
        if job_sen in want_sen:
            reasons.append(f"Seniority: {job_sen}")
    elif profile_seniority and job_sen:
        order = [
            "intern",
            "junior",
            "mid",
            "senior",
            "staff",
            "principal",
            "lead",
            "manager",
            "director",
            "executive",
        ]
        try:
            delta = abs(order.index(job_sen) - order.index(profile_seniority.lower()))
            comps["seniority"] = max(20.0, 100.0 - 20 * delta)
            if delta >= 2:
                reasons.append("Seniority gap")
        except ValueError:
            comps["seniority"] = 60.0
    else:
        comps["seniority"] = 60.0

    # Salary fit
    sal = job.get("salary") or {}
    jmin = sal.get("min")
    if c.salary and c.salary.min is not None and jmin is not None:
        # rough: job min vs criteria min (same period assumed after normalize)
        if float(jmin) >= float(c.salary.min) * 0.9:
            comps["salary"] = 90.0
            reasons.append("Salary fits")
        elif float(jmin) >= float(c.salary.min) * 0.7:
            comps["salary"] = 55.0
        else:
            comps["salary"] = 25.0
    elif jmin is None:
        comps["salary"] = 50.0
    else:
        comps["salary"] = 70.0

    # Freshness
    posted = job.get("posted_at")
    comps["freshness"] = 40.0
    if posted:
        if isinstance(posted, str):
            try:
                posted = datetime.fromisoformat(posted.replace("Z", "+00:00"))
            except ValueError:
                posted = None
        if posted is not None:
            if posted.tzinfo is None:
                posted = posted.replace(tzinfo=UTC)
            age_h = (datetime.now(UTC) - posted).total_seconds() / 3600
            if age_h < 72:
                comps["freshness"] = 100.0
                reasons.append("Posted < 72h")
            elif age_h < 168:
                comps["freshness"] = 75.0
            elif age_h < 720:
                comps["freshness"] = 50.0
            else:
                comps["freshness"] = 25.0

    # Location / remote
    comps["location"] = 55.0
    elig = job.get("remote_eligibility") or {}
    wm = job.get("work_mode")
    rem = c.remote_eligibility
    if rem.anywhere and (wm == "remote" or elig.get("anywhere")):
        comps["location"] = 95.0
        reasons.append("Remote eligible")
    elif rem.countries:
        allowed = {x.upper() for x in (elig.get("countries") or [])}
        want = {x.upper() for x in rem.countries}
        if want & allowed or elig.get("anywhere"):
            comps["location"] = 90.0
            reasons.append("Country eligible")
        elif wm == "remote":
            comps["location"] = 60.0
        else:
            comps["location"] = 30.0
    elif wm and c.work_modes and wm in c.work_modes:
        comps["location"] = 80.0

    return comps, reasons[:5]


def blend_score(
    comps: dict[str, float],
    weights: dict[str, float] | None = None,
    *,
    semantic: float | None = None,
    llm: float | None = None,
) -> float:
    w = clamp_weights(weights or {})
    parts = dict(comps)
    if semantic is not None:
        parts["semantic"] = semantic
    if llm is not None:
        parts["llm"] = llm
        # when LLM present, bump its weight from reserved/default
        if w.get("llm", 0) < 0.05:
            w = clamp_weights(
                {**w, "llm": 0.15, "semantic": max(0.05, w.get("semantic", 0.08) - 0.05)}
            )
    total = 0.0
    for k, wt in w.items():
        total += wt * float(parts.get(k, 50.0))
    return round(max(0.0, min(100.0, total)), 2)
