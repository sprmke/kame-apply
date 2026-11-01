# Settings → Integrations

**Status:** Documented (Phase 12b + 13 + 15)  
**Routes:** `/settings/integrations`, `/settings/integrations/consent`

## Behavior

- Shows MCP URL, Claude Code connect command, plugin install command (copy buttons).
- Agent inbox status (waiting / leased) and `/kame:work` command.
- Connected agents list (owner/admin): client name, scopes, revoke.
- Per-feature routing: server model vs My Claude (agent inbox).
- Consent page completes OAuth: pick profile + scopes, redirect back to the MCP client with an auth code.
- **Connect** browser extension: mints `ka_ext_…` and messages the extension (`NUXT_PUBLIC_EXTENSION_ID`).
- Platform autofill toggles (owner/admin): LinkedIn / Indeed / JobStreet / SEEK require terms acknowledgment.
- Apply runner tokens (owner/admin): create local/cloud `ka_run_…` (shown once), list, revoke.

## Save paths

| UI | API | DB |
| --- | --- | --- |
| Allow (consent) | `POST /api/v1/agent-bridge/consent` | `oauth_auth_codes`; deletes pending |
| Revoke | `POST /api/v1/agent-bridge/tokens/{id}/revoke` | `oauth_tokens.revoked_at` (+ family) |
| Routing | `PUT /api/v1/agent-bridge/routing` | `ai_feature_routing` |
| Create PAT | `POST /api/v1/agent-bridge/pats` | `oauth_tokens` (kind=pat); raw token once |
| Connect extension | `POST /api/v1/extension/tokens` + `chrome.runtime.sendMessage` | `extension_tokens` |
| Platform autofill | `PUT /api/v1/extension/platform-policies` | `workspace_platform_policies` |
| Create runner token | `POST /api/v1/runs/tokens` | `runner_tokens` (hash only; raw once) |
| Revoke runner token | `POST /api/v1/runs/tokens/{id}/revoke` | `runner_tokens.revoked_at` |

MCP tools use bearer tokens from `/mcp` OAuth (or PAT). Writes emit `activity_log` with `actor_type=agent`. Extension mutations use `actor_type=user`.

## Validation / RBAC

- Consent / enqueue: `data.write`
- Token list / revoke / PAT / routing write: `workspace.update` (managers)
- Routing / inbox read: `data.read`
- Extension token mint: `data.write`; platform policy put: `workspace.update`
- Runner token create/list/revoke: `workspace.update`
- Cross-tenant: RLS on `oauth_tokens`, `agent_tasks`, `ai_feature_routing`, `extension_tokens`, `workspace_platform_policies`, `runner_tokens`

## Agent parity

Equivalent MCP tools for workspace data; REST is for humans (consent, revoke, routing). Extension fill is browser-only.

## Edge cases

- Expired pending auth → 404 on consent.
- Revoked token → next MCP call 401.
- PAT is less preferred than OAuth; documented on the page as fallback.
- Missing `extensionId` or extension not installed → Connect shows an error; token may still be minted (revoke unused tokens).
- Enabling LinkedIn/Indeed/JobStreet/SEEK without acknowledging terms → 422.

## Implementation map

- Web: `apps/web/app/pages/settings/integrations.vue`, `…/consent.vue`
- API: `apps/api/app/agent_bridge/`, `apps/api/app/extension/`, `apps/api/app/runs/`
- Extension: `apps/extension/`
- Runner: `apps/runner/`
- Plugin: `integrations/claude-plugin/`
- CLI: `packages/kame-agent/`
- Docs: `docs/architecture/extension.md`, `docs/architecture/apply-runner.md`

## User-facing knowledge

Connect your Claude and your browser extension to this workspace. Both can draft and fill; you still click Submit and type anything sensitive.
