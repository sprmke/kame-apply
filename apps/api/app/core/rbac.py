"""Server-side RBAC: one place that says which workspace roles may perform which action.

Every endpoint (and later every MCP tool) names an action; the UI mirrors this table but never
replaces it. Add a row here, and a test row, when you add a capability (rbac-and-audit skill).
"""

from typing import Final

OWNER, ADMIN, MEMBER, VIEWER = "owner", "admin", "member", "viewer"
ALL_ROLES: Final = (OWNER, ADMIN, MEMBER, VIEWER)
MANAGERS: Final = (OWNER, ADMIN)
WRITERS: Final = (OWNER, ADMIN, MEMBER)

ACTIONS: Final[dict[str, tuple[str, ...]]] = {
    "workspace.read": ALL_ROLES,
    "workspace.update": MANAGERS,
    "workspace.delete": (OWNER,),
    "workspace.transfer": (OWNER,),
    "workspace.leave": ALL_ROLES,
    "members.read": ALL_ROLES,
    "members.invite": MANAGERS,
    "members.remove": MANAGERS,
    "members.change_role": MANAGERS,
    "ai_credentials.read": MANAGERS,
    "ai_credentials.manage": MANAGERS,
    "ai_usage.read": ALL_ROLES,
    "activity.read": MANAGERS,
    "data.read": ALL_ROLES,
    "data.write": WRITERS,
}


def can(role: str, action: str) -> bool:
    """Unknown actions and unknown roles are denied (fail closed)."""
    return role in ACTIONS.get(action, ())
