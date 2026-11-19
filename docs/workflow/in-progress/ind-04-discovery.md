# IND-4: Discovery for non-tech (scratchpad)

**Branch:** `ind/01-pack-foundation` · **Started:** 2026-11-13 · **Plan:** `docs/workflow/done/multi-industry-support.md` §7

## Shipped

- Track-aware board selection by `company_boards.industries` + pack `employer_tags`; explicit Track source toggles win.
- Layer 4 search: `search_jooble` and `search_adzuna` adapters with fixtures, terms notes, and a terms gate (`SEARCH_TERMS_ACKNOWLEDGED` + platform key, or fixture mode). A missing key disables the provider.
- Shared `source_query_cache` with a 6-hour default TTL; global, no tenant data.
- Query planner from titles + locations, capped per Track; `GET /tracks/{id}/where`.
- Rule classifier at ingest: `jobs.industry_hints`, `jobs.occupation_code`, `jobs.facets` (shifts, cuisine, kitchen type, station, credentials, pay includes).
- `source_coverage` table, seed rows for Technology and Hospitality PH/AE, `GET /sources/coverage`, Track coverage notice.
- Guided alert links `GET /sources/alerts/guide`; Culinary Agents setup guide.
- Migration `0041`; fixtures; unit tests and a full fixture discovery run that ingests and links chef jobs.

## Deliberately not done

- Live provider calls: terms/quota are unverified, so adapters stay behind the acknowledgement flag. No live staging M1 run.
- Hospitality employer directory seed (hotel/cruise career pages): needs URL validation and terms review.
- `job_fit` prompt v2 and LLM tiebreak; deterministic matching covers the current path.

## Verification

- `pnpm run ci:quality` passed (584 API tests, 3 skipped; web 18; extension 9; ui 21; evals-lite 103).
- Fixture discovery run ingested the two chef postings, filled `industry_hints`/facets/credentials, and linked both to the Sous Chef track.
- Manual UI: coverage notice showed "Few Hospitality and food jobs from our sources in Dubai yet." and Where we look showed "Sous Chef in Dubai" with Jooble/Adzuna setup status.
