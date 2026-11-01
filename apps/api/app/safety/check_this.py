"""Check-this: analyze recruiter messages, URLs, and GitHub repos (metadata only; never clone)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import urlparse

from app.safety.aggregate import RiskLevel
from app.safety.rules_engine import content_rule_hits
from app.safety.sanitize import sanitize_untrusted_text

_GITHUB_REPO = re.compile(
    r"(?i)https?://(?:www\.)?github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)"
)
_LIFECYCLE = ("preinstall", "postinstall", "prepare", "preuninstall", "postuninstall")


@dataclass
class CheckThisResult:
    level: RiskLevel
    score: float
    reasons: list[dict[str, Any]] = field(default_factory=list)
    advice: str = ""
    kind: Literal["message", "url", "repo"] = "message"


def analyze_text(raw: str) -> CheckThisResult:
    cleaned = sanitize_untrusted_text(raw).text
    hits = content_rule_hits(cleaned)
    score = float(sum(h.weight for h in hits))
    reasons = [
        {
            "signal": h.signal,
            "layer": "L1",
            "weight": h.weight,
            "evidence": h.evidence,
        }
        for h in hits
    ]

    # Take-home malware patterns (BeaverTail / InvisibleFerret style).
    blob = cleaned.lower()
    if re.search(
        r"(?i)clone.{0,80}(?:repo|repository|github\.com).{0,80}(?:npm|pip|yarn|pnpm)\s+install",
        blob,
    ) or (
        "clone" in blob
        and "github.com" in blob
        and re.search(r"(?i)(?:npm|pip|yarn|pnpm)\s+install", blob)
    ):
        score += 40
        reasons.append(
            {
                "signal": "takehome_malware_pattern",
                "layer": "check_this",
                "weight": 40,
                "evidence": "asks to clone a repo and run install before any interview",
            }
        )
    if re.search(r"(?i)disable\s+(?:your\s+)?(?:antivirus|firewall|defender)", blob):
        score += 45
        reasons.append(
            {
                "signal": "disable_security",
                "layer": "check_this",
                "weight": 45,
                "evidence": "asks to disable security software",
            }
        )
    if re.search(r"(?i)(?:fix\s+(?:camera|microphone|webcam)|clickfix|allow\s+pasting)", blob):
        score += 35
        reasons.append(
            {
                "signal": "clickfix",
                "layer": "check_this",
                "weight": 35,
                "evidence": "ClickFix-style camera/mic fix instructions",
            }
        )

    gh = _GITHUB_REPO.search(raw or "")
    if gh:
        repo_result = analyze_github_repo(gh.group("owner"), gh.group("repo").removesuffix(".git"))
        score += repo_result.score * 0.5
        reasons.extend(repo_result.reasons)
        kind: Literal["message", "url", "repo"] = "repo"
    elif re.search(r"(?i)https?://", raw or ""):
        kind = "url"
    else:
        kind = "message"

    score = max(0.0, min(100.0, score))
    level: RiskLevel = "green"
    if score >= 55:
        level = "red"
    elif score >= 25:
        level = "yellow"

    advice = (
        "Run take-home work only in a disposable sandbox (Codespace or VM). "
        "Never disable antivirus. We never clone or execute repos for you."
        if level != "green"
        else "No strong scam patterns found. Still verify the sender on a known channel."
    )
    return CheckThisResult(level=level, score=score, reasons=reasons, advice=advice, kind=kind)


def analyze_github_repo(owner: str, repo: str) -> CheckThisResult:
    """Read GitHub API metadata only. Never clones."""
    reasons: list[dict[str, Any]] = []
    score = 0.0
    skip = os.environ.get("ENVIRONMENT") == "test" or os.environ.get(
        "SAFETY_SKIP_NETWORK", ""
    ).lower() in {"1", "true"}

    if skip:
        # Deterministic fixture path for tests: flag common scam-shaped names.
        if any(x in repo.lower() for x in ("assessment", "takehome", "coding-test", "trial")):
            score += 15
            reasons.append(
                {
                    "signal": "new_takehome_repo",
                    "layer": "check_this",
                    "weight": 15,
                    "evidence": f"{owner}/{repo} (network skipped)",
                }
            )
        level: RiskLevel = "yellow" if score >= 25 else "green" if score < 15 else "yellow"
        return CheckThisResult(
            level=level if score < 55 else "red",
            score=score,
            reasons=reasons,
            advice="Network intel skipped in test mode.",
            kind="repo",
        )

    try:
        import httpx

        headers = {"Accept": "application/vnd.github+json", "User-Agent": "kame-apply-safety"}
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        with httpx.Client(timeout=5.0, headers=headers) as client:
            r = client.get(f"https://api.github.com/repos/{owner}/{repo}")
            if r.status_code != 200:
                reasons.append(
                    {
                        "signal": "repo_lookup_failed",
                        "layer": "check_this",
                        "weight": 5,
                        "evidence": f"HTTP {r.status_code}",
                    }
                )
                return CheckThisResult(
                    level="yellow",
                    score=10,
                    reasons=reasons,
                    advice="Could not load repo metadata. Treat with caution.",
                    kind="repo",
                )
            meta = r.json()
            stars = int(meta.get("stargazers_count") or 0)
            created = meta.get("created_at") or ""
            # Very new + low stars + assessment-shaped name.
            if stars < 5:
                score += 10
                reasons.append(
                    {
                        "signal": "low_stars",
                        "layer": "check_this",
                        "weight": 10,
                        "evidence": f"{stars} stars",
                    }
                )
            if created:
                reasons.append(
                    {
                        "signal": "repo_created",
                        "layer": "check_this",
                        "weight": 0,
                        "evidence": created,
                    }
                )

            # package.json lifecycle scripts via contents API (raw metadata).
            pkg = client.get(f"https://api.github.com/repos/{owner}/{repo}/contents/package.json")
            if pkg.status_code == 200:
                import base64
                import json

                content = pkg.json().get("content") or ""
                raw = base64.b64decode(content).decode("utf-8", errors="replace")
                data = json.loads(raw)
                scripts = data.get("scripts") or {}
                for key in _LIFECYCLE:
                    if key in scripts:
                        score += 35
                        reasons.append(
                            {
                                "signal": "lifecycle_script",
                                "layer": "check_this",
                                "weight": 35,
                                "evidence": f"{key}: {str(scripts[key])[:120]}",
                            }
                        )
    except Exception as exc:
        reasons.append(
            {
                "signal": "repo_lookup_error",
                "layer": "check_this",
                "weight": 5,
                "evidence": type(exc).__name__,
            }
        )
        score += 5

    score = max(0.0, min(100.0, score))
    level = "red" if score >= 55 else "yellow" if score >= 25 else "green"
    return CheckThisResult(
        level=level,
        score=score,
        reasons=reasons,
        advice=(
            "Run take-homes only in a disposable sandbox. We never clone or execute this repo."
        ),
        kind="repo",
    )


def analyze_url(url: str) -> CheckThisResult:
    host = ""
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        host = ""
    gh = _GITHUB_REPO.search(url or "")
    if gh:
        return analyze_github_repo(gh.group("owner"), gh.group("repo").removesuffix(".git"))
    # Reuse text analyzer on the URL string + host heuristics.
    base = analyze_text(url)
    if host.endswith(".tk") or host.endswith(".gq") or host.endswith(".ml"):
        base.score = min(100.0, base.score + 20)
        base.reasons.append(
            {
                "signal": "suspicious_tld",
                "layer": "check_this",
                "weight": 20,
                "evidence": host,
            }
        )
        base.level = "red" if base.score >= 55 else "yellow" if base.score >= 25 else "green"
    base.kind = "url"
    return base
