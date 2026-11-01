# Extension store submission packet

**Status:** Ready for store listing draft (dogfood on live sites before submit).

## Builds

```bash
pnpm --filter @kame/extension run build          # Chrome MV3 → apps/extension/.output/chrome-mv3
pnpm --filter @kame/extension run build:firefox  # Firefox → apps/extension/.output/firefox-mv3
```

Load unpacked from `.output/chrome-mv3` for dogfood. Record the extension id into `NUXT_PUBLIC_EXTENSION_ID`.

## Single purpose (Chrome Web Store)

Help job seekers save postings and fill application forms from their Kame Apply profile in their own browser session. The user reviews every form and clicks Submit.

## Limited use

- Reads page content only when the user clicks Save, Autofill, Answer insert, or I applied.
- Does not scrape logged-in feeds in the background.
- Does not solve CAPTCHAs, rotate proxies, or spoof fingerprints.
- Does not click Submit or Next on LinkedIn / Indeed / JobStreet / SEEK.
- Extension token is revocable from Settings → Integrations.

## Privacy

Public policy: `/legal/extension-privacy` (also linked from the store listing).

## Screenshots (capture before submit)

1. Side panel connected, Track/profile selectors visible (empty job page ok).
2. Greenhouse fixture: fields filled with source badges after Autofill.
3. Settings → Integrations: Connect + platform autofill toggles.
4. LinkedIn job page with Autofill disabled banner / skip state.
5. Risk banner when a red-flagged job is clipped (if available in dogfood data).

Place captures under `docs/design/screenshots/phase-13/` when taken.

## Firefox AMO

Same codebase (`build:firefox`). Listing copy mirrors Chrome. Request optional host permissions at first use.
