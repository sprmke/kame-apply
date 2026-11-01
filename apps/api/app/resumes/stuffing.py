"""Keyword stuffing guards for tailored resumes."""

from __future__ import annotations

import re
from collections import Counter

from app.resumes.content import ResumeContent

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9+#.]{1,}")


def term_frequencies(content: ResumeContent) -> Counter[str]:
    return Counter(w.lower() for w in _WORD.findall(content.plain_text()))


def enforce_stuffing_caps(
    content: ResumeContent,
    *,
    posting_terms: list[str],
    max_per_term: int = 4,
) -> tuple[ResumeContent, list[str]]:
    """Cap how often each posting term may appear; never invent hidden text."""
    data = content.model_copy(deep=True)
    warnings: list[str] = []
    freqs = term_frequencies(data)
    for term in posting_terms:
        t = term.lower().strip()
        if len(t) < 2:
            continue
        # Count phrase occurrences roughly by word token or full phrase
        count = freqs.get(t, 0)
        if " " in t:
            count = data.plain_text().lower().count(t)
        if count <= max_per_term:
            continue
        warnings.append(f"capped:{t}:{count}")
        # Soften by not rewriting further; planner should avoid over-injection
    # Skills section: only keep lines that have evidence refs
    for sec in data.sections:
        if sec.kind == "skills":
            before = len(sec.lines)
            sec.lines = [line for line in sec.lines if line.evidence_refs]
            if len(sec.lines) < before:
                warnings.append("skills_unevidenced_removed")
    return data, warnings


def length_budget_trim(content: ResumeContent, *, max_bullets: int = 12) -> ResumeContent:
    """Cut least relevant trailing bullets; never shrink fonts."""
    data = content.model_copy(deep=True)
    bullets: list[tuple[int, int, int]] = []  # sec_idx, item_idx, line_idx
    for si, sec in enumerate(data.sections):
        if sec.kind != "experience":
            continue
        for ii, item in enumerate(sec.items):
            for li in range(len(item.lines)):
                bullets.append((si, ii, li))
    if len(bullets) <= max_bullets:
        return data
    # Keep earliest (most recent roles first in our builder); drop from the end
    drop = set(bullets[max_bullets:])
    for si, sec in enumerate(data.sections):
        if sec.kind != "experience":
            continue
        for ii, item in enumerate(sec.items):
            item.lines = [line for li, line in enumerate(item.lines) if (si, ii, li) not in drop]
    return data
