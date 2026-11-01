# Claude Agent Bridge (Phase 12b)

Remote MCP + OAuth so the user's own Claude (Code / Desktop / claude.ai) can work against a Kame Apply workspace. The server never stores or relays Claude credentials.

## Endpoints

| Surface | Path |
| --- | --- |
| MCP Streamable HTTP | `POST/GET {api}/mcp/` |
| OAuth AS metadata | `{api}/mcp/.well-known/oauth-authorization-server` |
| Protected resource metadata | `{api}/mcp/.well-known/oauth-protected-resource` |
| Consent (web) | `{web}/settings/integrations/consent?pending_id=` |
| REST | `/api/v1/agent-bridge/*` |

Env: `AGENT_BRIDGE_ENABLED` (default true), `API_BASE_URL`, `WEB_BASE_URL`.

## Scopes

`profile:read|write`, `jobs:read|write`, `tracks:read|write`, `resume:read|write`, `answers:read|write`, `apply:read|write`, `admin`.

Tokens bind one user + workspace + profile (`subject = user:workspace:profile`). Switching requires a new grant.

## Tools (summary)

Context: `whoami`, `list_tracks`, `get_track`, `get_profile`, `get_answer_bank`, `get_voice_profile`.

Jobs: `search_jobs`, `get_job` (sanitized `<untrusted_data>` envelope), `assess_risk`, `shortlist_job`, `skip_job`.

Resume: `get_resume`, `get_lens_report`, `propose_resume_changes`, `render_resume`, `create_tailored_resume`.

Answers: `draft_answers`, `submit_answers`, `save_answer_to_bank`.

Applications: `list_applications`, `get_application_packet`, `log_application` (unconfirmed), `update_application_status`, `log_run_step`.

Inbox: `next_agent_task`, `complete_agent_task`, `fail_agent_task`.

Profile: `propose_profile_update`.

Writes are drafts / proposals with `activity_log.actor_type=agent`. No delete tools. No Submit. No sensitive fields.

## Agent inbox

`agent_tasks` with lease (`SELECT … FOR UPDATE SKIP LOCKED`, 15 min). Feature routing per workspace: `server` | `agent_inbox` for tailoring, answer_drafting, market_research, deep_fit_review, interview_prep.

## Clients

- Claude Code: `claude mcp add --transport http kame {api}/mcp`
- Plugin: `integrations/claude-plugin/`
- Optional CLI: `packages/kame-agent` (`kame-agent login|work|schedule`) — shells to local `claude -p` only

## Security

- PKCE, redirect URI validation, hashed tokens, revocation
- CI blocks Claude OAuth env token names in `apps/api`, `apps/web`, plugin, and `kame-agent`
- Untrusted job/email text always sanitized + enveloped
- Cross-tenant: token list and RLS on `oauth_tokens` / `oauth_auth_codes` / `agent_tasks` / `ai_feature_routing`
- OAuth AS token/code lookup: when both `app.user_id` and `app.workspace_id` are unset, RLS allows rows so the AS can resolve by hash only. List/revoke always set workspace context. Do not add unscoped queries against these tables.
- Consent and PAT creation are rate-limited
