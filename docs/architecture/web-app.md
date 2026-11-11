# Web app (apps/web)

Nuxt 4 SPA (`ssr: false`), Vue 3, Tailwind v4, Reka UI components from `packages/ui`. UI only: all business rules live in the API.

## Data and auth

- **API client:** `@kame/api-client` is generated from the FastAPI OpenAPI schema (`pnpm run gen:api-client`; CI checks drift). It exports SDK functions, Vue Query option helpers (`queries`), and Zod schemas (`schemas`).
- **`plugins/api.ts`** configures the client: base URL, `credentials: include`, `throwOnError`. A request interceptor adds `Authorization` (after a single-flight refresh when the token is near expiry) and `X-Workspace-Id`. A 401 from a non-auth route clears state and sends the user to `/login?next=`.
- **Tokens:** the access token lives in memory only (Pinia `auth` store). The refresh token is an HttpOnly cookie the browser sends to `/api/v1/auth/*`; a reload re-bootstraps through `/auth/refresh`. No tokens in `localStorage`.
- **Workspace:** the `workspace` store lists memberships and remembers the active id in `localStorage` (a convenience; the server re-checks membership on every request). Switching clears the Vue Query cache.
- **Route guard:** `middleware/auth.global.ts` bootstraps auth, redirects signed-out users to login, and keeps `/invite` reachable. Post-login targets pass `lib/next.ts::safeNext` (same-origin paths only).

## Forms and errors

VeeValidate + generated Zod schemas, extended with UX rules (e.g. password length). `plugins/zod.ts` turns Zod issues into catalog keys (`validation.*`), `useZodForm` translates them. API errors are `{ error: { code } }`; `useApiError` maps `errors.<code>` with a generic fallback. A Vitest test fails when a code the API can return has no message.

## i18n

`@nuxtjs/i18n`, English only for now (`i18n/locales/en.json`). No hard-coded UI strings. Dates, numbers and currency go through `useFormat` (`Intl`, user timezone). Copy follows `human-copy` and `ui-minimal-copy`: no em dashes, no exclamation marks.

## Shell

Layouts: `default` (rail, top bar with workspace switcher, command bar and profile menu, phone bottom bar) and `auth`. The command bar opens with Cmd/Ctrl+K. The Needs-you slot is reserved (count 0) until checkpoints exist in Phase 11. The Track switcher folder tabs arrive with Tracks (Phase 4).

## Testing

- Vitest: `packages/ui/tests` (components), `apps/web/tests` (i18n catalog integrity, smoke).
- Playwright (`pnpm run test:e2e`, needs `pnpm run dev:docker`): `e2e/acceptance.spec.ts` (acceptance scenarios 1 and 3 plus auth flows, invites, sessions), `e2e/shell.spec.ts` (scenario 4: no horizontal scroll at 375/820/1440, keyboard, command bar, theme, 404), `e2e/design.spec.ts` (visual snapshots of `/_design`), `e2e/visual-audit.spec.ts` (`pnpm run audit:ui`; real routes at 375/820/1440, fails on horizontal overflow), `e2e/career-profile.spec.ts` (Phase 3 profile surfaces), `e2e/tracks.spec.ts` (Phase 4), `e2e/discovery.spec.ts` (Phase 5 Run now / Sources), `e2e/matching.spec.ts` (Phase 6 Jobs board), `e2e/safety.spec.ts` (Phase 7 Safety), `e2e/studio.spec.ts` (Phase 8 Studio), `e2e/tailor.spec.ts` (Phase 9 Tailor). `e2e/capture-screens.spec.ts` (`CAPTURE=1`, optional `CAPTURE_PHASE=02|03|04|05|06|07|08|09|10|11|12`) regenerates `docs/design/screenshots/phase-0N/`.
- `pnpm run check:token-contrast` guards WCAG pairs in `tokens.css` across light, dark and high-contrast.
