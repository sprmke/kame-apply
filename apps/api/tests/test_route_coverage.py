"""Fail the build when a tenant route forgets workspace scoping.

Every route under /api/v1 must either depend on `workspace_context` (directly or through
`require_action`) or be listed in PUBLIC_OR_USER_SCOPED with a reason. New routers therefore
cannot ship without a conscious tenancy decision.
"""

from fastapi.routing import APIRoute

from app.core.security import workspace_context
from app.extension.deps import extension_workspace_context
from app.main import create_app
from app.runs.deps import runner_workspace_context
from tests.tenancy_app import build_test_app

# Every dependency that resolves a workspace from a credential and sets app.workspace_id.
# Token-scoped surfaces (extension, runner) resolve the workspace from their own credential instead
# of X-Workspace-Id, but they must still set the same RLS context before touching tenant rows.
WORKSPACE_CONTEXT_PROVIDERS = (
    workspace_context,
    extension_workspace_context,
    runner_workspace_context,
)

# path prefix -> why it is not workspace-scoped
PUBLIC_OR_USER_SCOPED: dict[str, str] = {
    "/api/v1/auth": "pre-authentication and session endpoints; identity exists before any workspace",
    "/api/v1/me": "the caller's own profile and sessions; user-scoped, not workspace-scoped",
    "/api/v1/webhooks": "inbound provider callbacks authenticated by HMAC/secret header; the address token resolves the workspace",
}
# Exact paths (not prefixes) that are user-scoped by design.
USER_SCOPED_EXACT: dict[str, str] = {
    "/api/v1/workspaces": "lists and creates the caller's own workspaces; no active workspace yet",
    "/api/v1/invitations/accept": "the invitee has no workspace until the token is accepted",
}


def _depends_on_workspace_context(dependant) -> bool:
    if dependant.call in WORKSPACE_CONTEXT_PROVIDERS:
        return True
    return any(_depends_on_workspace_context(d) for d in dependant.dependencies)


def _iter_api_routes(route_objects) -> list[tuple[str, APIRoute]]:
    """Expand every APIRoute, including routers that FastAPI includes lazily.

    FastAPI >= 0.162 stores `include_router` results as `_IncludedRouter` wrappers that are only
    flattened at request time, so iterating `app.routes` alone silently skips the whole v1 tree and
    turns this guard into a no-op. Walking `effective_candidates()` (and the older flat layout)
    keeps the check honest across FastAPI versions.
    """
    found: list[tuple[str, APIRoute]] = []
    for route in route_objects:
        if isinstance(route, APIRoute):
            found.append((route.path, route))
            continue
        candidates = getattr(route, "effective_candidates", None)
        if callable(candidates):
            found.extend(_iter_api_routes(candidates()))
            continue
        original = getattr(route, "original_route", None)
        if isinstance(original, APIRoute):
            found.append((getattr(route, "path", "") or original.path, original))
    return found


def _violations(app) -> list[str]:
    bad = []
    for path, route in _iter_api_routes(app.routes):
        if not path.startswith("/api/v1"):
            continue
        if path in USER_SCOPED_EXACT:
            continue
        if any(path.startswith(p + "/") or path == p for p in PUBLIC_OR_USER_SCOPED):
            continue
        if not _depends_on_workspace_context(route.dependant):
            bad.append(f"{sorted(route.methods or ())} {path}")
    return bad


def test_every_real_v1_route_is_workspace_scoped_or_allowlisted():
    assert _violations(create_app()) == []


def test_route_walker_reaches_every_v1_route():
    """A guard that silently sees zero routes would pass forever; assert it sees the real tree."""
    paths = {p for p, _ in _iter_api_routes(create_app().routes) if p.startswith("/api/v1")}
    assert len(paths) > 100


def test_probe_routes_are_scoped():
    app = build_test_app()
    assert _violations(app) == []


def test_checker_actually_detects_an_unscoped_route():
    app = build_test_app()

    @app.get("/api/v1/leaky")
    async def leaky():
        return {}

    assert _violations(app) == ["['GET'] /api/v1/leaky"]
