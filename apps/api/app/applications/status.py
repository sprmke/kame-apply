"""Application status state machine."""

from __future__ import annotations

from app.core.errors import AppError

STATUSES = (
    "draft",
    "ready",
    "in_progress",
    "needs_you",
    "submitted",
    "responded",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
    "ghosted",
    "job_closed",
)

# Canonical transitions. Regressions (e.g. interview → rejected → interview) need a note.
ALLOWED: dict[str, set[str]] = {
    "draft": {"ready", "withdrawn"},
    "ready": {"in_progress", "needs_you", "submitted", "withdrawn", "job_closed"},
    "in_progress": {"needs_you", "submitted", "withdrawn", "ready"},
    "needs_you": {"in_progress", "submitted", "withdrawn", "ready"},
    "submitted": {"responded", "interview", "rejected", "withdrawn", "ghosted"},
    "responded": {"interview", "offer", "rejected", "withdrawn", "ghosted", "submitted"},
    "interview": {"offer", "rejected", "withdrawn", "responded", "ghosted"},
    "offer": {"withdrawn", "rejected"},
    "rejected": {"interview", "withdrawn", "responded"},
    "withdrawn": set(),
    "ghosted": {"responded", "interview", "rejected", "withdrawn"},
    "job_closed": {"withdrawn", "ready"},
}

REGRESSIONS = {
    ("interview", "rejected"),
    ("interview", "responded"),
    ("rejected", "interview"),
    ("responded", "submitted"),
    ("offer", "rejected"),
}

KANBAN_COLUMNS = (
    "ready",
    "in_progress",
    "needs_you",
    "submitted",
    "responded",
    "interview",
    "offer",
    "rejected",
    "ghosted",
    "withdrawn",
)


def normalize(status: str) -> str:
    if status == "applied":
        return "submitted"
    return status


def assert_transition(current: str, new: str, *, note: str = "") -> None:
    cur = normalize(current)
    nxt = normalize(new)
    if cur == nxt:
        return
    allowed = ALLOWED.get(cur, set())
    if nxt not in allowed:
        raise AppError(
            "invalid_transition",
            f"Cannot move from {cur} to {nxt}",
            422,
        )
    if (cur, nxt) in REGRESSIONS and not (note or "").strip():
        raise AppError(
            "validation_error",
            "Add a note when moving backward in the pipeline",
            422,
        )
