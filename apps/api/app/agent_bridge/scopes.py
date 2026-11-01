"""OAuth scopes for the MCP agent bridge."""

from __future__ import annotations

ALL_SCOPES: tuple[str, ...] = (
    "profile:read",
    "profile:write",
    "jobs:read",
    "jobs:write",
    "tracks:read",
    "tracks:write",
    "resume:read",
    "resume:write",
    "answers:read",
    "answers:write",
    "apply:read",
    "apply:write",
    "admin",
)

DEFAULT_CONSENT_SCOPES: tuple[str, ...] = (
    "profile:read",
    "jobs:read",
    "jobs:write",
    "tracks:read",
    "resume:read",
    "resume:write",
    "answers:read",
    "answers:write",
    "apply:read",
    "apply:write",
)

# Tool name → required scopes (any one of a group, or all listed).
TOOL_SCOPES: dict[str, frozenset[str]] = {
    "whoami": frozenset(),
    "list_tracks": frozenset({"tracks:read", "admin"}),
    "get_track": frozenset({"tracks:read", "admin"}),
    "get_profile": frozenset({"profile:read", "admin"}),
    "get_answer_bank": frozenset({"answers:read", "admin"}),
    "get_voice_profile": frozenset({"profile:read", "admin"}),
    "search_jobs": frozenset({"jobs:read", "admin"}),
    "get_job": frozenset({"jobs:read", "admin"}),
    "assess_risk": frozenset({"jobs:read", "admin"}),
    "shortlist_job": frozenset({"jobs:write", "admin"}),
    "skip_job": frozenset({"jobs:write", "admin"}),
    "get_resume": frozenset({"resume:read", "admin"}),
    "get_lens_report": frozenset({"resume:read", "admin"}),
    "propose_resume_changes": frozenset({"resume:write", "admin"}),
    "render_resume": frozenset({"resume:read", "admin"}),
    "create_tailored_resume": frozenset({"resume:write", "admin"}),
    "draft_answers": frozenset({"answers:read", "admin"}),
    "submit_answers": frozenset({"answers:write", "admin"}),
    "save_answer_to_bank": frozenset({"answers:write", "admin"}),
    "list_applications": frozenset({"apply:read", "admin"}),
    "get_application_packet": frozenset({"apply:read", "admin"}),
    "log_application": frozenset({"apply:write", "admin"}),
    "update_application_status": frozenset({"apply:write", "admin"}),
    "log_run_step": frozenset({"apply:write", "admin"}),
    # Inbox tools need a write scope (not jobs:read alone).
    "next_agent_task": frozenset(
        {"admin", "resume:write", "answers:write", "apply:write", "profile:write", "jobs:write"}
    ),
    "complete_agent_task": frozenset(
        {"admin", "resume:write", "answers:write", "apply:write", "profile:write", "jobs:write"}
    ),
    "fail_agent_task": frozenset(
        {"admin", "resume:write", "answers:write", "apply:write", "profile:write", "jobs:write"}
    ),
    "propose_profile_update": frozenset({"profile:write", "admin"}),
}


def has_scope(granted: list[str] | set[str], required: frozenset[str]) -> bool:
    if not required:
        return True
    g = set(granted)
    return bool(g & required)
