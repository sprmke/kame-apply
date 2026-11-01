# Spike 7: WXT + Vue + shared `packages/ui`

**Date:** 2026-10-28 · **Decision: KEEP** · WXT 0.21.5, Vue 3.5, Tailwind 4.3. Code: `apps/extension`.

| Check | Result |
| --- | --- |
| Same component in both targets | `FnButton` from `@kame/ui` renders in the Nuxt app and in the WXT side panel, both importing `@kame/ui/tokens.css`. |
| Side-panel bundle | 114.6 kB raw, **39.6 kB gzipped** (JS + CSS), budget 300 kB gzipped. |
| Manifest | MV3, `side_panel`, permissions `sidePanel`, `storage`, `activeTab` only; no host permissions; asserted in `tests/manifest.test.ts`. |
| Type-check / lint / build | Pass in CI. |

Not yet checked: Firefox build (`pnpm --filter @kame/extension run build:firefox`) and visual parity screenshots; do both in Phase 13 when the real panel exists.
