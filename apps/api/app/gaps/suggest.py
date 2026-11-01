"""Suggest learning items for track must-skills missing from the profile."""

from __future__ import annotations

# Public learning resources only; never invent credentials.
_RESOURCES: dict[str, tuple[str, str]] = {
    "python": (
        "Build a small API that covers auth, CRUD, and tests.",
        "https://docs.python.org/3/tutorial/",
    ),
    "typescript": (
        "Convert a JS module to strict TypeScript with tests.",
        "https://www.typescriptlang.org/docs/",
    ),
    "kubernetes": (
        "Deploy a sample app with a Deployment, Service, and Ingress locally.",
        "https://kubernetes.io/docs/tutorials/",
    ),
    "sql": (
        "Write queries that join, aggregate, and explain plans on a sample schema.",
        "https://www.postgresql.org/docs/current/tutorial.html",
    ),
    "go": (
        "Ship a CLI or HTTP service with tests and a README.",
        "https://go.dev/doc/tutorial/",
    ),
    "react": (
        "Build a small interactive UI with accessible forms.",
        "https://react.dev/learn",
    ),
}


def suggest_for_skill(skill: str) -> tuple[str, str]:
    key = skill.strip().casefold()
    if key in _RESOURCES:
        return _RESOURCES[key]
    for k, v in _RESOURCES.items():
        if k in key or key in k:
            return v
    return (
        f"Practice {skill} with a small portfolio project you can cite as evidence.",
        "",
    )
