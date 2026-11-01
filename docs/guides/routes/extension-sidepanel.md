# Extension side panel

**Status:** Documented (Phase 13)  
**Entrypoint:** `apps/extension/entrypoints/sidepanel/`

## Behavior

- Shows connect prompt until Settings → Integrations → Connect completes the handshake.
- Track and profile selectors (from `GET /api/v1/extension/session`).
- **Save to Track**: extracts job hints from the active tab → `POST /clip`.
- **Autofill**: extracts fields → `POST /runs/plan-page` → fills with badges; never Submit.
- **I applied**: `POST /log-applied`.
- Risk banner when a clipped job carries a red/high risk level.

## Save paths

| UI | API | DB |
| --- | --- | --- |
| Connect (web) | `POST /extension/tokens` + runtime message | `extension_tokens` |
| Save to Track | `POST /extension/clip` | `jobs`, `track_jobs` |
| Autofill | `POST /extension/runs/plan-page` | `apply_runs`, `apply_run_steps`, `form_signatures` |
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
