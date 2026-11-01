---
name: wxt-extension
description: WXT (MV3) extension structure, messaging, permissions, content-script patterns, store packaging. Phase 13.
---

# WXT extension

Read `docs/phases/phase-13-browser-extension.md`. Use `context7` for current WXT APIs.

- Layout: `apps/extension/entrypoints/{background,sidepanel,page-bridge}`; UI in Vue using `packages/ui` and the same tokens as web.
- **Permissions**: minimal and optional where possible; per-site host permissions requested at use time; never required `<all_urls>`. Inject page extract/fill via unlisted `page-bridge.js` + `scripting.executeScript`.
- **Messaging**: typed messages between page bridge, background, and side panel; page scripts never hold tokens.
- **Auth**: separate, scope-limited, revocable extension token; stored in extension storage; never reuse the web session.
- **Page scripts**: act only on user gesture on the user's own session at human pace; no background crawling of logged-in pages; no evasion (`job-site-access.mdc`).
- **Field brain stays server-side**: extension extracts fields, calls `plan-page`, fills the returned values, and raises checkpoints.
- **Packaging**: Chrome/Edge/Firefox builds from one codebase; store listing copy states data use plainly. See `docs/architecture/extension.md`.
