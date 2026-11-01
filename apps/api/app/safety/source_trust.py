"""L2 source trust: ATS host allowlist + verified company domain."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.safety.rules_engine import ats_host_patterns


@dataclass(frozen=True)
class SourceTrust:
    score_delta: int  # negative lowers scam score (more trust)
    label: str
    verified_ats: bool
    evidence: str


def _host_matches(host: str, pattern: str) -> bool:
    host = host.lower().rstrip(".")
    pattern = pattern.lower()
    if pattern.startswith("*."):
        suffix = pattern[1:]  # .example.com
        return host.endswith(suffix) or host == pattern[2:]
    return host == pattern


def assess_source_trust(
    *,
    apply_url: str,
    canonical_url: str | None = None,
    source_kind: str | None = None,
    company_domain: str | None = None,
    company_verified: bool = False,
) -> SourceTrust:
    urls = [u for u in (apply_url, canonical_url) if u]
    hosts = []
    for u in urls:
        try:
            hosts.append(urlparse(u).hostname or "")
        except ValueError:
            continue
    hosts = [h for h in hosts if h]
    patterns = ats_host_patterns()
    on_ats = any(_host_matches(h, p) for h in hosts for p in patterns)
    if on_ats and (company_verified or source_kind == "ats"):
        return SourceTrust(
            score_delta=-25,
            label="verified_ats",
            verified_ats=True,
            evidence=hosts[0] if hosts else apply_url,
        )
    if on_ats:
        return SourceTrust(
            score_delta=-15,
            label="known_ats",
            verified_ats=False,
            evidence=hosts[0] if hosts else apply_url,
        )
    if company_domain and any(
        (h == company_domain or h.endswith("." + company_domain)) for h in hosts
    ):
        return SourceTrust(
            score_delta=-10,
            label="company_careers",
            verified_ats=False,
            evidence=hosts[0],
        )
    return SourceTrust(score_delta=0, label="unknown", verified_ats=False, evidence="")
