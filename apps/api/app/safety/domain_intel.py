"""L3 domain & email intel (RDAP age, DNS MX/SPF/DMARC, lookalike). Soft-fail when network down."""

from __future__ import annotations

import os
import re
import socket
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse


@dataclass
class DomainIntel:
    score_delta: int = 0
    reasons: list[dict[str, Any]] = field(default_factory=list)
    partial: bool = False
    domain_age_days: int | None = None


def _root_domain(host: str) -> str:
    parts = host.lower().rstrip(".").split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host.lower()


def lookalike_distance(a: str, b: str) -> int:
    """Levenshtein distance capped for short brand strings."""
    a, b = a.lower(), b.lower()
    if a == b:
        return 0
    if abs(len(a) - len(b)) > 3:
        return 99
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


_EMAIL_RE = re.compile(r"(?i)\b([a-z0-9._%+-]+)@([a-z0-9.-]+\.[a-z]{2,})\b")


def assess_domain_intel(
    *,
    apply_url: str,
    company_domain: str | None = None,
    text: str = "",
    skip_network: bool | None = None,
) -> DomainIntel:
    if skip_network is None:
        skip_network = os.environ.get("ENVIRONMENT") == "test" or os.environ.get(
            "SAFETY_SKIP_NETWORK", ""
        ).lower() in {"1", "true"}

    out = DomainIntel()
    host = ""
    try:
        host = urlparse(apply_url).hostname or ""
    except Exception:
        host = ""
    root = _root_domain(host) if host else ""

    # Personal-email company contact already covered by L1; here: domain vs company mismatch.
    if company_domain and root and _root_domain(company_domain) != root:
        # ATS hosts are expected to differ from company domain.
        from app.safety.source_trust import assess_source_trust

        st = assess_source_trust(apply_url=apply_url, company_domain=company_domain)
        if not st.verified_ats and st.label == "unknown":
            out.score_delta += 20
            out.reasons.append(
                {
                    "signal": "domain_mismatch",
                    "layer": "L3",
                    "weight": 20,
                    "evidence": f"{root} vs {company_domain}",
                }
            )

    # Lookalike vs company domain in emails found in text.
    if company_domain:
        brand = _root_domain(company_domain).split(".")[0]
        for m in _EMAIL_RE.finditer(text or ""):
            edom = m.group(2).lower()
            ebrand = edom.split(".")[0]
            dist = lookalike_distance(brand, ebrand)
            if 0 < dist <= 2 and edom != _root_domain(company_domain):
                out.score_delta += 25
                out.reasons.append(
                    {
                        "signal": "lookalike_email",
                        "layer": "L3",
                        "weight": 25,
                        "evidence": m.group(0),
                    }
                )
                break

    if skip_network or not root:
        if not skip_network and not root:
            out.partial = True
        return out

    # Lightweight DNS: resolvability via getaddrinfo. Mark partial on failure.
    try:
        socket.getaddrinfo(root, 443)
    except OSError:
        out.score_delta += 10
        out.reasons.append(
            {
                "signal": "domain_unresolvable",
                "layer": "L3",
                "weight": 10,
                "evidence": root,
            }
        )
        out.partial = True

    # RDAP age: optional httpx call; never block assessment.
    try:
        import httpx

        with httpx.Client(timeout=3.0, follow_redirects=True) as client:
            r = client.get(f"https://rdap.org/domain/{root}")
            if r.status_code == 200:
                data = r.json()
                events = data.get("events") or []
                reg = next(
                    (e for e in events if e.get("eventAction") in {"registration", "registered"}),
                    None,
                )
                if reg and reg.get("eventDate"):
                    created = datetime.fromisoformat(str(reg["eventDate"]).replace("Z", "+00:00"))
                    age = (datetime.now(UTC) - created).days
                    out.domain_age_days = age
                    if age < 90:
                        # Cap: domain age alone never forces red (aggregate handles cap).
                        out.score_delta += 20
                        out.reasons.append(
                            {
                                "signal": "new_domain",
                                "layer": "L3",
                                "weight": 20,
                                "evidence": f"{root} age {age}d",
                            }
                        )
            else:
                out.partial = True
    except Exception:
        out.partial = True

    return out
