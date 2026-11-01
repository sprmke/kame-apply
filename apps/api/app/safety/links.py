"""L4 link reputation: redirect resolve (no JS), ATS allowlist, optional Safe Browsing / URLhaus."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from app.safety.source_trust import assess_source_trust

_SHORTENERS = {
    "bit.ly",
    "t.co",
    "tinyurl.com",
    "goo.gl",
    "ow.ly",
    "rebrand.ly",
    "cutt.ly",
}


@dataclass
class LinkIntel:
    score_delta: int = 0
    reasons: list[dict[str, Any]] = field(default_factory=list)
    partial: bool = False
    final_url: str | None = None


def assess_links(
    *,
    apply_url: str,
    skip_network: bool | None = None,
) -> LinkIntel:
    if skip_network is None:
        skip_network = os.environ.get("ENVIRONMENT") == "test" or os.environ.get(
            "SAFETY_SKIP_NETWORK", ""
        ).lower() in {"1", "true"}

    out = LinkIntel(final_url=apply_url)
    host = ""
    try:
        host = (urlparse(apply_url).hostname or "").lower()
    except Exception:
        host = ""

    if host in _SHORTENERS:
        out.score_delta += 15
        out.reasons.append(
            {
                "signal": "url_shortener",
                "layer": "L4",
                "weight": 15,
                "evidence": host,
            }
        )

    st = assess_source_trust(apply_url=apply_url)
    if st.verified_ats or st.label == "known_ats":
        return out

    if skip_network:
        return out

    from app.core.ssrf import is_safe_outbound_url

    if not is_safe_outbound_url(apply_url):
        out.partial = True
        out.score_delta += 20
        out.reasons.append(
            {
                "signal": "ssrf_blocked_url",
                "layer": "L4",
                "weight": 20,
                "evidence": "private_or_metadata",
            }
        )
        return out

    # Resolve redirects without JS; re-check SSRF on every hop (never follow into private IPs).
    try:
        import httpx

        current = apply_url
        with httpx.Client(timeout=4.0, follow_redirects=False) as client:
            for _ in range(5):
                if not is_safe_outbound_url(current):
                    out.partial = True
                    out.score_delta += 20
                    out.reasons.append(
                        {
                            "signal": "ssrf_blocked_redirect",
                            "layer": "L4",
                            "weight": 20,
                            "evidence": "private_or_metadata",
                        }
                    )
                    return out
                r = client.head(current)
                if r.is_redirect:
                    nxt = r.headers.get("location")
                    if not nxt:
                        break
                    current = str(httpx.URL(current).join(nxt))
                    continue
                current = str(r.url)
                break
            out.final_url = current
            final_host = (urlparse(out.final_url).hostname or "").lower()
            if final_host in _SHORTENERS:
                out.score_delta += 10
                out.reasons.append(
                    {
                        "signal": "redirect_shortener",
                        "layer": "L4",
                        "weight": 10,
                        "evidence": final_host,
                    }
                )
    except Exception:
        out.partial = True

    # Safe Browsing / URLhaus: optional; mark partial if keys unset or call fails.
    sb_key = os.environ.get("GOOGLE_SAFE_BROWSING_API_KEY", "")
    if sb_key and not skip_network:
        try:
            import httpx

            body = {
                "client": {"clientId": "kame-apply", "clientVersion": "0.0.0"},
                "threatInfo": {
                    "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE"],
                    "platformTypes": ["ANY_PLATFORM"],
                    "threatEntryTypes": ["URL"],
                    "threatEntries": [{"url": apply_url}],
                },
            }
            with httpx.Client(timeout=4.0) as client:
                r = client.post(
                    f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={sb_key}",
                    json=body,
                )
                if r.status_code == 200 and r.json().get("matches"):
                    out.score_delta += 50
                    out.reasons.append(
                        {
                            "signal": "safe_browsing_hit",
                            "layer": "L4",
                            "weight": 50,
                            "evidence": apply_url,
                        }
                    )
        except Exception:
            out.partial = True
    else:
        # No key in local/dev: not a failure.
        pass

    try:
        import httpx

        with httpx.Client(timeout=3.0) as client:
            r = client.post(
                "https://urlhaus-api.abuse.ch/v1/url/",
                data={"url": apply_url},
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("query_status") == "ok" and data.get("url_status") == "online":
                    out.score_delta += 50
                    out.reasons.append(
                        {
                            "signal": "urlhaus_hit",
                            "layer": "L4",
                            "weight": 50,
                            "evidence": apply_url,
                        }
                    )
    except Exception:
        out.partial = True

    return out
