# Browser extension

**Phase:** 13 · **Code:** `apps/extension` (WXT MV3 + Vue), `apps/api/app/extension/`

## Role

Runs in the user's own browser session. Clips jobs, autofills forms from Career Profile + answer bank, inserts drafted answers, and logs applications. The user always clicks Submit. Field values are decided server-side (`POST /api/v1/extension/runs/plan-page`).

## Auth

1. Settings → Integrations → **Connect** mints a scoped `ka_ext_…` token (hashed at rest, revocable, ~90 day TTL).
2. Web sends `{ type: "kame.connect", token, workspaceId, apiBase }` via `chrome.runtime.sendMessage(extensionId, …)` (`externally_connectable`).
3. Extension stores the token in `browser.storage.local` and calls the API with `Authorization: Bearer ka_ext_…` + `X-Workspace-Id`.
4. Content scripts never hold tokens; the background service worker owns the API client.

Set `NUXT_PUBLIC_EXTENSION_ID` to the unpacked/store extension id so Connect works.

## API surface (`/api/v1/extension`)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/tokens` | JWT write | Mint extension token (raw once) |
| GET | `/tokens` | JWT read | List own tokens |
| POST | `/tokens/{id}/revoke` | JWT write | Revoke |
| GET | `/session` | JWT or ext | Tracks + profiles for the panel |
| GET/PUT | `/platform-policies` | JWT (put: manage) | Per-platform autofill opt-in |
| GET | `/platform-terms` | JWT | Restricted-platform copy |
| POST | `/clip` | JWT or ext write | Save job URL/title/company (+ optional JSON-LD) to a Track |
| POST | `/runs/start` | JWT or ext write | Start apply run |
| POST | `/runs/plan-page` | JWT or ext write | Extracted fields → fill instructions |
| POST | `/log-applied` | JWT or ext write | Mark applied (`method=extension`) |
| POST | `/answer-insert` | JWT or ext write | Draft for focused question |

## Platform policy

LinkedIn, Indeed, JobStreet, SEEK: **autofill off by default**. Owner/admin must acknowledge terms and enable. Even when enabled, the extension fills only on user click and never clicks Next/Submit. Greenhouse / Lever / Ashby / Workday / Workable / SmartRecruiters / generic: autofill allowed without opt-in (still never Submit).

## Permissions

Manifest: `sidePanel`, `storage`, `activeTab`, `scripting`. Host access is `optional_host_permissions`, requested per origin on first use. No required `host_permissions`. Page extract/fill runs via the unlisted `page-bridge.js` script injected with `scripting.executeScript` after the user grants the site (not a declared `content_scripts` entry).

## Packaging

- Chrome/Edge: `pnpm --filter @kame/extension run build`
- Firefox: `pnpm --filter @kame/extension run build:firefox`
- Store packet: `docs/architecture/extension-store.md` (privacy, limited use, screenshots)
- Public privacy page: `/legal/extension-privacy`

## Invariants

- No evasion tooling (`job-site-access.mdc`).
- Sensitive fields → checkpoint; values never logged (step log stores redacted placeholders).
- Page content leaves the browser only on explicit user action (clip / autofill / answer insert).
- Cross-tenant: extension tokens are workspace-bound; wrong `X-Workspace-Id` → 403; RLS on tenant tables.
