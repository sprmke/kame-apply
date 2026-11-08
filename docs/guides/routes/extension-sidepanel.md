# Extension side panel

**Status:** Documented (Phase 13)  
**Entrypoint:** `apps/extension/entrypoints/sidepanel/`

## Behavior

- Shows connect prompt until Settings → Integrations → Connect completes the handshake.
- Track and profile selectors (from `GET /api/v1/extension/session`).
- **Save to Track**: extracts job hints from the active tab (URL, title, company, and JSON-LD description; arbitrary page prose is ignored) → `POST /clip`.
- **Autofill**: extracts fields → `POST /runs/plan-page` → fills with badges; never Submit.
- **Answer**: asks the focused field's question, gets a draft from `POST /answer-insert`, and inserts it into that field. AI-restricted questions are refused.
- **I applied**: `POST /log-applied`.
- Risk banner when the clipped job has a `job_risk` level (reads the safety assessment, not job metadata).

## Save paths

| UI | API | DB |
| --- | --- | --- |
| Connect (web) | `POST /extension/tokens` + runtime message | `extension_tokens` |
| Save to Track | `POST /extension/clip` | `jobs`, `track_jobs` |
| Autofill | `POST /extension/runs/plan-page` | `apply_runs`, `apply_run_steps`, `form_signatures` |
| Answer | `POST /extension/answer-insert` | none (draft only) |
| I applied | `POST /extension/log-applied` | `applications` (+ events) |

## RBAC

Extension token inherits the user's workspace role. Clip/autofill need `data.write`. Platform policy opt-in needs `workspace.update`.

## Agent parity

No MCP equivalent for page fill (browser-only). Clip/log-applied overlap with tracker APIs.

## Edge cases

- Restricted platforms skip fill until opt-in.
- Token revoked → reconnect prompt.
- Host permission denied → status error; no silent retry through another identity.

## Implementation map

- Extension: `apps/extension/`
- API: `apps/api/app/extension/`
- Architecture: `docs/architecture/extension.md`
