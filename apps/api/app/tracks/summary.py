"""Deterministic one-sentence summary from CriteriaV1 (LLM polish is optional later)."""

from __future__ import annotations

from app.tracks.criteria import CriteriaV1, TitleSpec


def _title_words(titles: list[TitleSpec]) -> list[str]:
    return [t.title for t in titles if not t.exclude]


def summarize(criteria: CriteriaV1) -> str:
    roles = _title_words(criteria.titles)
    if not roles and criteria.occupations:
        roles = [o.label or o.code for o in criteria.occupations]
    role_part = ", ".join(roles[:3]) if roles else "Any role"
    if len(roles) > 3:
        role_part += f" (+{len(roles) - 3})"

    bits: list[str] = [role_part]

    if criteria.seniority:
        bits.append("/".join(criteria.seniority[:3]))

    modes = list(criteria.work_modes)
    rem = criteria.remote_eligibility
    if rem.anywhere:
        bits.append("remote worldwide")
    elif rem.countries or rem.regions:
        places = [*rem.regions, *rem.countries]
        bits.append("remote from " + ", ".join(places[:4]))
    elif modes:
        bits.append("/".join(m.replace("_", "-") for m in modes))

    if criteria.locations:
        locs = [loc.place for loc in criteria.locations[:3]]
        bits.append("in " + ", ".join(locs))

    if criteria.visa_sponsorship is True:
        bits.append("visa sponsorship")
    if criteria.relocation is True:
        bits.append("relocation ok")

    if criteria.salary and criteria.salary.min is not None:
        s = criteria.salary
        bits.append(f"≥ {s.min:g} {s.currency}/{s.period}")

    must = criteria.skills.must[:4]
    if must:
        bits.append("must: " + ", ".join(must))

    if criteria.companies.exclude_agencies:
        bits.append("no agencies")

    sentence = ". ".join(bits) if len(bits) == 1 else bits[0] + ": " + "; ".join(bits[1:])
    if not sentence.endswith("."):
        sentence += "."
    return sentence
