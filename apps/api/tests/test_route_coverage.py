"""Fail the build when a tenant route forgets workspace scoping.

Every route under /api/v1 must either depend on `workspace_context` (directly or through
`require_action`) or be listed in PUBLIC_OR_USER_SCOPED with a reason. New routers therefore
cannot ship without a conscious tenancy decision.
"""

from fastapi.routing import APIRoute

from app.core.security import workspace_context
from app.main import create_app
from tests.tenancy_app import build_test_app

# path prefix -> why it is not workspace-scoped
PUBLIC_OR_USER_SCOPED: dict[str, str] = {
    "/api/v1/auth": "pre-authentication and session endpoints; identity exists before any workspace",
    "/api/v1/me": "the caller's own profile and sessions; user-scoped, not workspace-scoped",
}
# Exact paths (not prefixes) that are user-scoped by design.
USER_SCOPED_EXACT: dict[str, str] = {
    "/api/v1/workspaces": "lists and creates the caller's own workspaces; no active workspace yet",
    "/api/v1/invitations/accept": "the invitee has no workspace until the token is accepted",
}


def _depends_on_workspace_context(dependant) -> bool:
    if dependant.call is workspace_context:
        return True
    return any(_depends_on_workspace_context(d) for d in dependant.dependencies)


def _violations(app) -> list[str]:
    bad = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/v1"):
            continue
        if route.path in USER_SCOPED_EXACT:
            continue
        if any(route.path.startswith(p + "/") or route.path == p for p in PUBLIC_OR_USER_SCOPED):
            continue
        if not _depends_on_workspace_context(route.dependant):
            bad.append(f"{sorted(route.methods or ())} {route.path}")
    return bad


def test_every_real_v1_route_is_workspace_scoped_or_allowlisted():
    assert _violations(create_app()) == []


def test_probe_routes_are_scoped():
    app = build_test_app()
    assert _violations(app) == []


def test_checker_actually_detects_an_unscoped_route():
    app = build_test_app()

    @app.get("/api/v1/leaky")
    async def leaky():
        return {}

    assert _violations(app) == ["['GET'] /api/v1/leaky"]
