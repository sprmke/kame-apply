"""Pure assessment pipeline (no DB). Used by service + mid-run hooks."""

from __future__ import annotations

from typing import Any

from app.safety.aggregate import RiskAssessment, aggregate, uncertain_band
from app.safety.domain_intel import assess_domain_intel
from app.safety.links import assess_links
from app.safety.ml_classifier import classify_text
from app.safety.rules_engine import content_rule_hits
from app.safety.sanitize import (
    flags_as_risk_reason,
    sanitize_untrusted_html,
    sanitize_untrusted_text,
)
from app.safety.source_trust import assess_source_trust


def assess_job_text(
    *,
    title: str,
    description_html: str = "",
    description_text: str = "",
    apply_url: str,
    canonical_url: str | None = None,
    source_kind: str | None = None,
    company_domain: str | None = None,
    company_verified: bool = False,
    salary: dict[str, Any] | None = None,
    community_delta: int = 0,
    community_reasons: list[dict[str, Any]] | None = None,
    extra_signals: list[dict[str, Any]] | None = None,
    run_network: bool = True,
    run_llm: bool = False,
) -> RiskAssessment:
    if description_html:
        san_html = sanitize_untrusted_html(description_html)
        san_text = sanitize_untrusted_text(description_text or "")
        # Prefer the longer cleaned body; scammers often put bait in text, layout in HTML.
        combined = san_html.text
        if len(san_text.text) > len(combined):
            combined = san_text.text
        elif san_text.text and san_text.text not in combined:
            combined = f"{combined}\n{san_text.text}".strip()
        from types import SimpleNamespace

        san = SimpleNamespace(
            text=combined,
            flags=tuple(dict.fromkeys([*san_html.flags, *san_text.flags])),
            injection_lines_removed=san_html.injection_lines_removed
            + san_text.injection_lines_removed,
            hidden_removed=san_html.hidden_removed + san_text.hidden_removed,
        )
    else:
        san = sanitize_untrusted_text(description_text)
    blob = f"{title}\n{san.text}"

    hits = content_rule_hits(blob)
    inj = flags_as_risk_reason(san.flags)
    if inj:
        # Represent as a synthetic hit if pattern didn't already catch it.
        if not any(h.signal == "ai_injection" for h in hits):
            from app.safety.rules_engine import RuleHit

            hits.append(
                RuleHit(
                    rule_id="ai_injection_sanitize",
                    signal="ai_injection",
                    weight=int(inj["weight"]),
                    evidence=str(inj["evidence"]),
                )
            )

    source = assess_source_trust(
        apply_url=apply_url,
        canonical_url=canonical_url,
        source_kind=source_kind,
        company_domain=company_domain,
        company_verified=company_verified,
    )
    domain = assess_domain_intel(
        apply_url=apply_url,
        company_domain=company_domain,
        text=blob,
        skip_network=not run_network,
    )
    links = assess_links(apply_url=apply_url, skip_network=not run_network)
    ml = classify_text(blob)

    missing_salary = not (salary or {})
    assessment = aggregate(
        content_hits=hits,
        source=source,
        domain=domain,
        links=links,
        ml=ml,
        community_delta=community_delta,
        community_reasons=community_reasons,
        missing_salary_only=missing_salary and not hits,
    )

    if extra_signals:
        for sig in extra_signals:
            w = int(sig.get("weight") or 20)
            assessment.score = min(100.0, assessment.score + w)
            assessment.reasons.append(sig)
        if assessment.score >= 55:
            assessment.level = "red"
        elif assessment.score >= 25:
            assessment.level = "yellow"

    llm_result = None
    if run_llm and uncertain_band(assessment):
        llm_result = _llm_judge_stub(blob, assessment)
        assessment = aggregate(
            content_hits=hits,
            source=source,
            domain=domain,
            links=links,
            ml=ml,
            community_delta=community_delta,
            community_reasons=community_reasons,
            llm=llm_result,
            missing_salary_only=False,
        )

    assessment.layers["sanitize"] = {
        "flags": list(san.flags),
        "injection_removed": san.injection_lines_removed,
        "hidden_removed": san.hidden_removed,
    }
    return assessment


def _llm_judge_stub(text: str, current: RiskAssessment) -> dict[str, Any]:
    """Cheap structured judge placeholder; real PydanticAI wire-up when AI configured."""
    from app.safety.sanitize import for_ai_context

    # Delimit even for the stub so future LLM wiring cannot see raw instructions.
    _ = for_ai_context(text, kind="job_posting")
    return {
        "level": current.level if current.level != "green" else "yellow",
        "summary": "Uncertain band; human should review reasons",
        "model": "stub",
    }
