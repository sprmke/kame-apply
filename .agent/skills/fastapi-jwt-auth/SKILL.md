---
name: fastapi-jwt-auth
description: FastAPI JWT access/refresh, Google OAuth, extension tokens, and workspace membership dependencies.
---

# FastAPI auth

- Dependencies in `app/core/security.py`: `get_current_user`, `WorkspaceContext` (resolves `X-Workspace-Id`, verifies an active membership and role), `require_role(*roles)`.
- Access token short-lived, refresh token rotated on use with reuse detection. Passwords hashed with argon2. Google OAuth via Authlib.
- Re-check `workspace_members.is_active` and role on every request; an unexpired JWT never outranks a revoked membership.
- Extension tokens are separate, scope-limited, revocable, and hashed at rest. Never reuse the web session token in the extension.
- MCP / agent-bridge tokens are OAuth tokens issued by our own authorization server; same membership re-check.
- No Supabase, Clerk, or Auth0. Never log tokens.
