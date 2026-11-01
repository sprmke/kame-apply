"""Pure policy checks for auto-submit (PRD F8)."""

from __future__ import annotations

from typing import Any

from app.autosubmit.schemas import PolicyReason, PolicyVerdict
from app.runs.ats import NO_AUTO_SUBMIT

DEFAULT_SCORE_THRESHOLD = 75.0
DEFAULT_DRY_RUNS = 10


def _ok(code: str, detail: str) -> PolicyReason:
    return PolicyReason(code=code, ok=True, detail=detail)


def _fail(code: str, detail: str) -> PolicyReason:
    return PolicyReason(code=code, ok=False, detail=detail)


def evaluate(
    *,
    autonomy: str,
    ats: str,
    risk_level: str,
    match_score: float | None,
    score_threshold: float,
    answers_all_approved: bool,
    checkpoint_fired: bool,
    company_cap_exceeded: bool,
    daily_cap_exceeded: bool,
    job_open: bool,
    job_fresh_enough: bool,
    kill_switch_track: bool,
    kill_switch_workspace: bool,
    global_enabled: bool,
    live_enabled: bool,
    dry_run_remaining: int,
) -> PolicyVerdict:
    reasons: list[PolicyReason] = []

    if autonomy != "auto_submit":
        reasons.append(_fail("autonomy", "Track autonomy is not auto_submit"))
    else:
        reasons.append(_ok("autonomy", "Track autonomy is auto_submit"))

    if not global_enabled:
        reasons.append(_fail("global_kill", "Global auto-submit is disabled"))
    else:
        reasons.append(_ok("global_kill", "Global auto-submit enabled"))

    if kill_switch_workspace:
        reasons.append(_fail("workspace_kill", "Workspace kill switch is on"))
    else:
        reasons.append(_ok("workspace_kill", "Workspace kill switch off"))

    if kill_switch_track:
        reasons.append(_fail("track_kill", "Track kill switch is on"))
    else:
        reasons.append(_ok("track_kill", "Track kill switch off"))

    if ats in NO_AUTO_SUBMIT or ats in {"unknown", ""}:
        reasons.append(
            _fail(
                "platform",
                f"ATS '{ats or 'unknown'}' is not allowlisted for auto-submit",
            )
        )
    else:
        reasons.append(_ok("platform", f"ATS '{ats}' is allowlisted"))

    if risk_level != "green":
        reasons.append(_fail("risk", f"Risk level is {risk_level}, need green"))
    else:
        reasons.append(_ok("risk", "Risk is green"))

    if match_score is None:
        reasons.append(_fail("score", "No match score"))
    elif match_score < score_threshold:
        reasons.append(
            _fail("score", f"Score {match_score:.0f} below threshold {score_threshold:.0f}")
        )
    else:
        reasons.append(_ok("score", f"Score {match_score:.0f} ≥ {score_threshold:.0f}"))

    if not answers_all_approved:
        reasons.append(_fail("answers", "Free-text answers need batch or bank approval"))
    else:
        reasons.append(_ok("answers", "All free-text answers approved"))

    if checkpoint_fired:
        reasons.append(_fail("checkpoint", "A checkpoint fired; fall back to assist"))
    else:
        reasons.append(_ok("checkpoint", "No checkpoint fired"))

    if company_cap_exceeded:
        reasons.append(_fail("company_cap", "Per-company application cap reached"))
    else:
        reasons.append(_ok("company_cap", "Company cap ok"))

    if daily_cap_exceeded:
        reasons.append(_fail("daily_cap", "Daily application cap reached"))
    else:
        reasons.append(_ok("daily_cap", "Daily cap ok"))

    if not job_open:
        reasons.append(_fail("job_open", "Job is not open"))
    else:
        reasons.append(_ok("job_open", "Job is open"))

    if not job_fresh_enough:
        reasons.append(_fail("freshness", "Job is too old for auto-submit policy"))
    else:
        reasons.append(_ok("freshness", "Job is fresh enough"))

    hard_ok = all(r.ok for r in reasons)
    dry_run = False
    allow = False
    if hard_ok:
        if not live_enabled or dry_run_remaining > 0:
            dry_run = True
            allow = False  # never click submit in dry-run
            reasons.append(
                _ok(
                    "dry_run",
                    f"Dry-run mode ({dry_run_remaining} remaining); would submit but will not",
                )
            )
        else:
            allow = True
            reasons.append(_ok("live", "Live auto-submit enabled"))
    else:
        reasons.append(_fail("blocked", "One or more policy checks failed"))

    summary = (
        "Would auto-submit (dry-run)"
        if dry_run and hard_ok
        else ("Auto-submit allowed" if allow else "Auto-submit blocked; assist mode")
    )
    return PolicyVerdict(
        allow_submit=allow, dry_run=dry_run and hard_ok, reasons=reasons, summary=summary
    )


def settings_from_track(settings: dict[str, Any] | None) -> dict[str, Any]:
    s = (settings or {}).get("auto_submit") if isinstance(settings, dict) else {}
    if not isinstance(s, dict):
        s = {}
    return {
        "live_enabled": bool(s.get("live_enabled", False)),
        "dry_run_remaining": int(s.get("dry_run_remaining", DEFAULT_DRY_RUNS)),
        "score_threshold": float(s.get("score_threshold", DEFAULT_SCORE_THRESHOLD)),
        "kill_switch": bool(s.get("kill_switch", False)),
        "anomaly_paused": bool(s.get("anomaly_paused", False)),
        "anomaly_reason": s.get("anomaly_reason"),
    }
