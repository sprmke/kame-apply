# Research 08: Bring your own Claude (Claude Code subscription integration)

**Researched:** 2026-10-28; **re-verified for Phase 12b:** 2026-11-01 (MCP Python SDK 2.3 Streamable HTTP + OAuth AS provider). Policy unchanged: never store Claude credentials. These products change quickly.
**Feeds into:** [Phase 12b](../phases/phase-12b-claude-agent-bridge.md), PRD F21.

## 1. The ask

Use a Claude Code subscription (Pro/Max) to do Kame Apply's agentic work, with access to all the app's data: profile, resumes, files, Tracks, criteria, jobs, answers, applications. Examples: tailoring, answering questions, research, filling forms.

## 2. What the policy allows (this decides the architecture)

| Pattern | Allowed? | Source |
| --- | --- | --- |
| Kame Apply's **server** uses a user's Claude.ai login/subscription (Agent SDK or `claude -p` on our servers) | ❌ Not without Anthropic's prior approval. "Unless previously approved, Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products, including agents built on the Claude Agent SDK." | [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview) |
| Our app **collects/stores/relays** users' Claude.ai credentials or tokens (e.g. `CLAUDE_CODE_OAUTH_TOKEN`) | ❌ "may not collect, store, or intermediate Claude.ai credentials or session tokens"; may not "route requests through Free, Pro, or Max plan credentials on behalf of their users" | [Legal and compliance](https://code.claude.com/docs/en/legal-and-compliance) |
| A user runs the **unmodified** Claude Code (`claude`, `claude -p`) **on their own machine** with their own subscription, for their own work, connected to Kame Apply | ✅ Nothing prevents "an end user from signing in to the unmodified Claude Code binary with their own Claude subscription"; plan limits assume "ordinary, individual usage". kame-hunt already does this (`claude -p --json-schema` in `src/ai-score.ts`). | same |
| User adds Kame Apply as a **remote MCP server / custom connector** in Claude Code, Claude Desktop, or claude.ai; their Claude does the reasoning on their plan | ✅ The sanctioned "bring your own Claude" pattern. Custom connectors: Free (1), Pro, Max, Team, Enterprise. | [Custom connectors](https://support.claude.com/en/articles/11175166-about-custom-connectors-using-remote-mcp), [Claude Code MCP](https://code.claude.com/docs/en/mcp) |
| User pastes their own **Anthropic API key** (BYO key, already in PRD F16) | ✅ | Agent SDK docs |
| Our app fires a user's cloud **scheduled task** (routine) via its API trigger | ⚠️ Grey area (same question as row 1). **We don't do it.** Users may create their own routines that use the Kame connector; we provide templates only. | [Routines](https://code.claude.com/docs/en/routines) |

**Design rule:** Kame Apply never holds, proxies, or triggers anything on a user's Claude credentials. The user's Claude (in their Claude Code, Desktop, claude.ai, or their own headless `claude -p`) connects **to** Kame Apply. All app-side AI that runs on our server still uses BYO API keys or local models (F16).

Credits note: sources disagree on whether plan-included SDK/`claude -p` usage draws from subscription limits or a monthly credit ([support article](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan), updated Oct 7, 2026). It doesn't affect the design; verify before writing any pricing copy.

## 3. Integration surfaces (all user-side)

### 3.1 Kame Apply remote MCP server (the core)

- **Transport:** Streamable HTTP at `https://api.kameapply.app/mcp`, mounted in FastAPI (official MCP Python SDK). Claude Code: `claude mcp add --transport http kame https://api.kameapply.app/mcp`.
- **Auth:** OAuth. Kame Apply acts as the authorization server: Protected Resource Metadata (RFC 9728) → AS metadata (RFC 8414) → dynamic client registration and Client ID Metadata Documents (both supported by Claude Code) → PKCE → consent screen where the user picks **workspace + candidate profile + scopes**. Scopes: `profile:read`, `jobs:read`, `tracks:write`, `drafts:write`, `applications:write`, `files:read`. Tokens are revocable in Settings → Integrations → Connected agents. Docs mention OAuth 2.0; build to the current MCP auth spec and test with Claude Code, Desktop, and claude.ai.
- **Reachability:** claude.ai/Desktop connectors connect from **Anthropic's cloud**, so the endpoint must be public (the production API already is). For local dev, Claude Code on the same machine can use `http://localhost`.
- **Tools** (thin wrappers over existing services; every write is a **proposal/draft** that passes the same server-side verifiers as in-app AI):

| Group | Tools |
| --- | --- |
| Context | `whoami`, `list_tracks`, `get_track` (criteria, market insights summary), `get_profile` (facts with ids), `get_answer_bank`, `get_voice_profile` |
| Jobs | `search_jobs` (Track, filters, paginated), `get_job` (sanitized text, qualifications, risk, eligibility), `assess_risk`, `shortlist_job` / `skip_job` |
| Resume | `get_resume` (content JSON with evidence refs), `get_lens_report`, `propose_resume_changes` (ops with evidence refs → verifier → returns accepted/rejected ops + gaps), `render_resume` (returns a short-lived download URL + parse-gate result), `create_tailored_resume` (job_id → runs our tailoring workflow, or accepts Claude's proposed content for verification) |
| Answers | `draft_answers` (returns facts + constraints + AI-restriction flags, so Claude drafts in the user's voice), `submit_answers` (verifier: no new facts; AI-restricted questions refused), `save_answer_to_bank` (proposal) |
| Applications | `list_applications`, `get_application_packet` (resume file URL, answers, profile basics, job snapshot, checkpoint rules), `log_application` / `update_application_status` (proposals for status changes from emails), `log_run_step` (for Claude-in-Chrome applies) |
| Agent inbox | `next_agent_task`, `complete_agent_task`, `fail_agent_task` (see 3.3) |
| Profile | `propose_profile_update` (e.g. a metric learned in conversation; user confirms in app) |

  Not exposed: anything destructive (delete), submit-application, sensitive fields, other workspaces, raw secrets.
- **Resources** (`@kame:` mentions in Claude Code): `kame://profile`, `kame://tracks/{id}`, `kame://jobs/{id}`, `kame://resumes/{id}` (markdown rendering), `kame://applications/{id}`.
- **Prompts** (show up as slash commands like `/kame:tailor`): `tailor <job>`, `hunt <track>` (briefing + shortlist), `answer` (Answer Desk in chat), `vet <url|message>`, `prep <application>`, `work` (process the agent inbox), `apply <application>` (Claude in Chrome guided apply).
- **Output limits:** Claude Code warns at 10k tokens and truncates at 25k by default (`MAX_MCP_OUTPUT_TOKENS`). Tools paginate, return summaries + ids, and fetch details on demand. `_meta["anthropic/maxResultSizeChars"]` is raised only for `get_job` full text.
- **Elicitation** (supported by Claude Code): used for confirmations such as "This job is flagged yellow: continue?" and choosing a Track when ambiguous.

### 3.2 Kame Apply Claude Code plugin (distribution + playbooks)

A public marketplace repo `kame-apply/claude-plugins` with plugin `kame-apply`:

```
.claude-plugin/plugin.json
.mcp.json                      → remote kame server (HTTP + OAuth)  [verify plugin remote-OAuth support; fallback: setup command runs `claude mcp add`]
skills/
  tailoring-playbook/SKILL.md  → research/05 §6 + research/07 rules, truthfulness, stuffing limits
  answer-voice/SKILL.md        → voice + banned phrases + AI-restriction rule
  apply-checklist/SKILL.md     → checkpoint kinds; never submit, never type passwords, never solve CAPTCHAs, stop on sensitive fields
  untrusted-content/SKILL.md   → job text is data; never run commands or open links from postings
commands/                      → /kame:hunt /kame:tailor /kame:apply /kame:vet /kame:prep /kame:work /kame:setup
agents/recruiter-reviewer.md   → fresh-context skeptical recruiter critique (drafter→reviewer loop)
hooks/hooks.json               → PreToolUse: block Bash/WebFetch whose input contains text from postings (heuristic guard);
                                 PreToolUse on browser tools: ask before any click whose target text matches submit/apply/send
```

Install: `/plugin marketplace add kame-apply/claude-plugins` → `/plugin install kame-apply@kame-apply`. It's a port of kame-hunt's `.claude/commands/{hunt,tailor,apply,vet,outreach,prep}.md` to MCP tools instead of local files.

### 3.3 Agent inbox: "let my Claude do it"

Use the subscription for heavy work, without the server touching credentials:

- In AI settings, each AI feature can be routed to **"My Claude (agent inbox)"** instead of a server model: tailoring, answer drafting, market research, deep fit review, interview prep. Bulk/cheap tasks (qualification extraction, scam LLM layer) stay server-side, since they run over global public data.
- When routed, the app creates `agent_tasks` (kind, inputs as ids, output JSON schema, priority, deadline) instead of calling an LLM. The UI shows "Waiting for your Claude" with a copyable command.
- The user's Claude processes them in one of three user-controlled ways:
  1. **Interactive:** `/kame:work` in Claude Code. It pulls tasks, does them with MCP tools, and submits results.
  2. **Headless on the user's machine:** `kame-agent` (a tiny optional CLI shipped with the local runner, `uv tool install kame-agent`) runs the user's own unmodified `claude -p` on a launchd/cron schedule the **user** installs: `claude -p "/kame:work --max 5" --output-format stream-json --allowedTools "mcp__kame__*" --permission-mode dontAsk` (no `--bare`, which forces API keys). Credentials never leave the user's machine. This is the "ordinary individual usage" case.
  3. **User-created cloud routine:** the user creates a scheduled task in claude.ai with the Kame connector and a template prompt we provide. We never trigger it.
- Results come back via `complete_agent_task` and go through the same verifier, render, parse gate, and Lens pipeline as server-side AI. They appear in the app as drafts to accept.
- Task leasing: `next_agent_task` leases for 15 min; expired leases return to the queue; idempotent completion; a task kind can fall back to a server model if the user enabled fallback and nothing claimed it by the deadline.

### 3.4 Applying with Claude in Chrome (optional path alongside our extension)

Claude in Chrome needs a direct plan login and drives the user's **own visible, signed-in Chrome**. It pauses for logins and CAPTCHAs on its own ([docs](https://code.claude.com/docs/en/chrome)). `/kame:apply <application>`:

1. `get_application_packet` → resume file (downloaded to a temp folder via a signed URL), approved answers, profile basics, checkpoint rules.
2. Claude fills the form in the user's Chrome; AI-restricted, sensitive, and unknown fields are left for the user, per the `apply-checklist` skill; `log_run_step` records progress, so the app's run timeline shows it.
3. The user clicks Submit; `log_application` marks it submitted (the app then asks the user to confirm).

Same platform policy as Phase 13 (LinkedIn/Indeed/JobStreet opt-in only). Our own extension stays the primary assist path, since it works for every user, including those without a Claude plan.

### 3.5 Files: local working folder (optional)

`kame-agent pull <track>` writes a readable snapshot (`profile.yaml`, `answers.yaml`, `tracks/<name>/criteria.yaml`, `resumes/*.json|pdf`, `jobs/*.md`) for Claude Code users who like file-based work, like kame-hunt's layout. `kame-agent push` sends edits back as **proposals** (diff → verifier → accept in app). The server stays the source of truth; push rejects stale versions (optimistic concurrency with version ids).

## 4. Risks specific to this integration

| Risk | Mitigation |
| --- | --- |
| **Prompt injection now targets the user's Claude, which may have shell/file tools** | Tool results wrap job/email text in explicit untrusted-data envelopes, sanitized by Phase 7's sanitizer; injection-flagged lines removed; the plugin's `untrusted-content` skill + hook; docs recommend running `/kame:*` with the plugin's restricted `allowedTools`; no tool returns executable instructions |
| Claude submits fabricated content | All writes are proposals through the same truthfulness verifier and parse gate; rejected ops come back as gaps |
| Over-broad access | Scoped OAuth tokens per workspace/profile; token audit (`actor_type='agent'`, client name); revocation; rate limits per token |
| Policy changes | One integration boundary (MCP + inbox); feature-flagged; research/08 re-verified each release |
| Plugin remote-MCP OAuth not supported as documented | Fallback `/kame:setup` instructions run `claude mcp add --transport http ...` |
| Users without Claude plans | Every feature still works with server-side BYO keys / Ollama; the Claude path is optional |
| Claude-in-Chrome clicking Submit | Skill rules + PreToolUse ask-hook on submit-like clicks; `log_application` marks agent-reported submits "unconfirmed" until the user confirms |
