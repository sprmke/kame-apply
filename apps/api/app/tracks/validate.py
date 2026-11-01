"""Criteria validation warnings (contradictions, keyword syntax). Never hard-blocks save
except missing role signal when creating from empty."""

from __future__ import annotations

import re
from typing import Any

from app.tracks.criteria import CriteriaV1

_TOKEN = re.compile(r"^[A-Za-z0-9][\w.+#/\-]{0,63}$")
_BOOL_OPS = frozenset({"AND", "OR", "NOT"})


def validate_criteria(criteria: CriteriaV1) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []

    if not criteria.has_role_signal():
        warnings.append(
            {
                "code": "missing_role",
                "message": "Add at least one title or occupation",
                "suggestion": "Describe the role in the text box or pick a template",
            }
        )

    modes = set(criteria.work_modes)
    rem = criteria.remote_eligibility
    if "on_site" in modes and rem.anywhere:
        warnings.append(
            {
                "code": "contradiction_onsite_remote",
                "message": "On-site and remote-anywhere conflict",
                "suggestion": "Remove on-site or turn off remote anywhere",
            }
        )
    if "on_site" in modes and not criteria.locations and not rem.countries:
        warnings.append(
            {
                "code": "onsite_without_place",
                "message": "On-site roles need a location or eligible country",
                "suggestion": "Add a city or country",
            }
        )

    if criteria.salary:
        s = criteria.salary
        if s.min is not None and s.max is not None and s.min > s.max:
            warnings.append(
                {
                    "code": "salary_range_inverted",
                    "message": "Salary min is greater than max",
                    "suggestion": "Swap or clear one bound",
                }
            )
        if s.rate_missing:
            warnings.append(
                {
                    "code": "salary_rate_missing",
                    "message": f"No FX rate for {s.currency}; original kept, USD filter skipped",
                    "suggestion": None,
                }
            )

    for field, expr in (
        ("include_expr", criteria.keywords.include_expr),
        ("exclude_expr", criteria.keywords.exclude_expr),
    ):
        if expr:
            err = validate_boolean_expr(expr)
            if err:
                warnings.append(
                    {
                        "code": "keyword_syntax",
                        "message": err,
                        "suggestion": "Use AND / OR / NOT with parentheses and quoted phrases",
                        "path": f"keywords.{field}",
                    }
                )

    overlap = set(x.casefold() for x in criteria.skills.must) & set(
        x.casefold() for x in criteria.skills.exclude
    )
    if overlap:
        warnings.append(
            {
                "code": "skill_must_and_exclude",
                "message": "Skills appear in both must and exclude: " + ", ".join(sorted(overlap)),
                "suggestion": "Remove them from one list",
            }
        )

    return warnings


def validate_boolean_expr(expr: str) -> str | None:
    """Lightweight boolean keyword expression check. Returns an error message or None."""
    s = expr.strip()
    if not s:
        return None
    if s.count("(") != s.count(")"):
        return "Unbalanced parentheses"
    # Tokenize roughly: quoted strings, parens, operators, bare words
    tokens: list[str] = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch.isspace():
            i += 1
            continue
        if ch in "()":
            tokens.append(ch)
            i += 1
            continue
        if ch in "\"'":
            quote = ch
            j = i + 1
            while j < len(s) and s[j] != quote:
                j += 1
            if j >= len(s):
                return "Unclosed quote"
            tokens.append(s[i + 1 : j])
            i = j + 1
            continue
        j = i
        while j < len(s) and not s[j].isspace() and s[j] not in "()\"'":
            j += 1
        tokens.append(s[i:j])
        i = j
    if not tokens:
        return "Empty expression"
    depth = 0
    expect_term = True
    for tok in tokens:
        upper = tok.upper()
        if tok == "(":
            if not expect_term:
                return "Unexpected '('"
            depth += 1
            continue
        if tok == ")":
            if expect_term or depth == 0:
                return "Unexpected ')'"
            depth -= 1
            expect_term = False
            continue
        if upper in _BOOL_OPS:
            if upper == "NOT":
                if not expect_term:
                    return "NOT must precede a term"
                continue
            if expect_term:
                return f"Unexpected {upper}"
            expect_term = True
            continue
        if not expect_term:
            return f"Missing AND/OR before '{tok}'"
        if not (_TOKEN.match(tok) or " " in tok or any(c in tok for c in ".+#/")):
            if not tok:
                return "Empty token"
        expect_term = False
    if expect_term:
        return "Expression ends with an operator"
    if depth != 0:
        return "Unbalanced parentheses"
    return None
