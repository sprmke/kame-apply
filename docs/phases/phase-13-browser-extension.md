# Phase 13: Browser extension: clip, autofill, answer insert, log applied

**Status:** Done · **Release:** R1 · **Depends on:** 11, 12 · **Features:** F4 (Layer 5), F8 (assist via extension), F9, F11 · **Reference:** [`research/03`](../research/03-apply-engine-and-live-view.md) §1–2, §6

## Goal

In the user's own browser (where they're logged in to LinkedIn, JobStreet, Indeed, Workday...), the extension saves jobs, fills application forms from the profile and tailored materials, inserts answers, and logs applications. The user reviews and clicks Submit, so nothing needs bypassing.

## Acceptance scenarios

1. Install → connect to the account (one click from Settings → Integrations) → side panel shows the active workspace/Track.
2. On a LinkedIn job page → **Save to Track** → only URL + title + company are captured; the app resolves the same job on the employer's ATS and ingests it from there (falls back to the minimal record if not found). See [`review/plan-critique-and-risks.md`](../review/plan-critique-and-risks.md) §2.1.
3. On a Greenhouse application → **Autofill** → standard fields filled, the tailored resume (if one exists for this job) uploaded, custom questions filled from the answer bank or drafted (drafts highlighted for review), sensitive fields untouched and marked, AI-restricted questions left blank with a note. Each filled field shows a small source badge.
4. **Per-platform policy table** (settings): LinkedIn Easy Apply / Indeed / JobStreet Quick Apply autofill is **off by default**. When the workspace owner opts in (explicit terms acknowledgment), the extension fills only on user click, one step at a time, and never clicks Next or Submit on those platforms. Applying on the employer ATS is suggested when the job exists there.
5. After submission, the confirmation page is detected (or the user clicks "I applied") → application logged with resume version and answers.
6. Risk: opening a red-flagged job shows a banner in the side panel.

## Tasks

- [x] WXT project (MV3, Chrome/Edge/Firefox), shared `packages/ui` (Vue components + Field Notes tokens), side panel Vue app, background service worker (API client with token refresh), content scripts per platform/ATS.
- [x] Auth handshake: web app → `chrome.runtime.sendMessage` (externally_connectable) → scoped, revocable extension token; workspace switcher in panel.
- [x] Field extraction in content script (same `ExtractedField` schema as runner) → `POST /runs/plan-page` (server brain) → fill instructions → apply with native setters + dispatched input/change events (React-controlled inputs), file upload via DataTransfer.
- [x] Platform/ATS modules: LinkedIn Easy Apply, Indeed Apply, JobStreet/SEEK, Greenhouse, Lever, Ashby, Workday, Workable, SmartRecruiters, generic fallback.
- [x] Clipper: page → sanitized job text + URL + structured hints (JSON-LD if present) → ingest endpoint.
- [x] Answer insert: focused field → Answer Desk draft → insert.
- [x] Applied detection per platform (confirmation selectors/URLs) + manual button.
- [x] Permissions: `optional_host_permissions` requested per site at first use; minimal default permissions.
- [x] Packaging: store listings, privacy policy page, limited-use disclosure, screenshots; Firefox AMO build.

## Edge cases & failure modes

- Shadow DOM, iframes (Workday, embedded Greenhouse on company sites) → `all_frames` content scripts with frame-aware extraction.
- ATS resume parsing overwrites fields after upload → re-extract and re-verify after upload.
- Rate of use on LinkedIn → no background actions at all; extension acts only on user click on the current page.
- Token expiry while filling → silent refresh; failure → "reconnect" prompt, no partial silent failures.
- Site updates break selectors → generic fallback + error telemetry (no PII) → adapter fix.
- Multiple Tracks match the job → the side panel asks which Track (remembers per company).

## Security & privacy

No page content sent except on explicit user action (clip/autofill); sensitive values never read or sent; telemetry has no field values.

## Testing

Content-script unit tests on saved HTML fixtures per platform; Playwright E2E loading the unpacked extension against local fixture forms; manual checklist on live sites (dogfood) before store submission.

## Docs to update

`docs/architecture/extension.md` (new), skill `wxt-extension`, privacy policy.

## Exit criteria

- [x] Scenarios 1–6 covered by implementation + automated tests (API/extension); Firefox build produces a loadable package; store submission packet ready. Live Chrome/Firefox dogfood on real sites remains before store submit (see Testing).

## Built

- Migration `0024`: `extension_tokens`, `workspace_platform_policies`, `form_signatures`, `apply_runs`, `apply_run_steps` (+ RLS).
- API: `apps/api/app/extension/` (tokens, session, policies, clip, plan-page, log-applied, answer-insert).
- Extension: side panel, background messaging, unlisted `page-bridge.js` inject (no required host permissions), extract/fill utils, platform detection.
- Web: Integrations Connect + platform policy toggles; `/legal/extension-privacy`.
- Docs: `docs/architecture/extension.md`, `extension-store.md`, route guides.
- Tests: `apps/api/tests/test_extension.py`, extension fixture extract/fill + manifest; `pnpm run ci:quality` green.
