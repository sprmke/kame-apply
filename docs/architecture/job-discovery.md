# Job discovery (Phase 5)

Ingest open jobs from compliant sources into a global pool, dedupe them, and link matches to Tracks.

## Layers

| Layer | Adapters (v1) |
| --- | --- |
| 1 ATS | greenhouse, lever, ashby, workable, smartrecruiters, recruitee |
| 2 boards | remotive, remoteok, himalayas, arbeitnow, jobicy, muse |
| 3 career pages | career_jsonld (JobPosting JSON-LD) |
| 4 search | search_jooble, search_adzuna (keyword + location) |

Adapter package: `packages/py-core/kame_core/sources/`. Each adapter carries a terms note, descriptive UA, and fails closed on block signals (never evasion). Layer 4 adapters are gated: they run only when a platform key exists **and** `SEARCH_TERMS_ACKNOWLEDGED=true`, or when a fixture directory is supplied for tests. A missing key disables that provider cleanly (P7). Career-page crawling checks `robots.txt` first (`robots_allowed`, cached per host for an hour) and raises a block signal on a disallow. Career-page boards also send a conditional `HEAD` with the stored ETag/Last-Modified and skip the fetch on `304`.

## Data model

**Global (no RLS):** `sources`, `companies`, `company_boards`, `jobs`, `job_sources`, `country_source_registry`, `source_coverage`, `source_query_cache`.

Industry fields: `companies.industries`, `company_boards.industries`, `jobs.industry_hints`, `jobs.occupation_code`, `jobs.facets` (cuisine, station, kitchen type, shifts, credentials, pay includes). They are filled by the rule classifier in `jobs/classify.py` at ingest. Existing rows are backfilled to Technology.

**Tenant (RLS):** `track_sources`, `track_jobs`, `discovery_runs`.

Apply URL preference: company ATS > career page > board (`jobs/dedupe.py`). Dedupe requires company + normalized title + location compatibility + SimHash distance ≤ 8, so two requisitions in different cities do not merge. One bad record rolls back to a savepoint, not the whole run; a failed run is persisted with `status=failed`.

Closed detection: two consecutive poll misses on a board/source → `jobs.status=closed`. Applied to ATS/board sources and to the Layer-2 feeds (Remotive, RemoteOK, Arbeitnow, Jobicy, Muse, Himalayas).

## Directory

Directory seed: 64 curated boards (status `active`, validated) plus generated candidate slugs (status `candidate`, `validation_method=seed_unverified`). Only active, validated boards are polled; candidates exist so the directory can grow once a board is confirmed. `GET /sources/directory/stats` reports `boards_active` and `boards_candidate` separately.

Monthly CDX import: `scripts/sources/refresh_directory.py --cdx-jsonl …`.

User add: `POST /api/v1/sources/careers` with a careers URL (ATS detector).

## Workflows

`POST /api/v1/tracks/{id}/discover` runs `discover_track` (service + optional DBOS enqueue when `DBOS_SYSTEM_DATABASE_URL` is set). Progress on the run row; SSE at `/api/v1/discovery-runs/{id}/events`.

Track-aware boards: `_boards_for_run` picks boards whose `industries` overlap the Track pack's `employer_tags`, plus user-added boards with no tag. A Track's explicit source toggles still win. Without toggles, the pack's `sources.adapters` are the allowlist, so a Hospitality track does not poll Remotive or tech ATS feeds.

Interim Track link: rule filter on criteria titles/skills/work modes (`jobs/link.py`). Phase 6 ranking refines it.

Layer 4: `sources/search_service.py` builds up to 6 keyword + location queries from the Track's titles and locations, checks the global `source_query_cache` (default 6 hours), calls the provider, upserts through the same dedupe path, and links the Track. The same cache serves every workspace.

Coverage: `source_coverage(source_key, country, industry, coverage, note)` powers `GET /api/v1/sources/coverage` and the Track's "Few jobs" notice. `GET /api/v1/tracks/{id}/where` shows the planned queries, adapters, and whether each is configured. `GET /api/v1/sources/alerts/guide` returns prefilled public search URLs for the person to create their own alerts; Kame never signs in for them.

## Admin

`GET /api/v1/sources/health` (managers): success/error counts, latency, circuit, block signals.

UI: `/settings/sources`, Track settings Sources toggles, Track detail **Run now**, the **Where we look** disclosure, and the coverage notice that links to Settings > Alerts.

## Fixtures

Recorded responses under `apps/api/tests/fixtures/sources/<adapter>/` (CI never calls live boards).


## Provider terms checked (2026-11-13)

- **Jooble.** Regional REST API: `POST https://{region}.jooble.org/api/{key}`. A key is valid only for the domain that issued it, so PH and AE need their own keys (`JOOBLE_API_KEY_PH`, `JOOBLE_API_KEY_AE`). The official help center lists 100 requests per day per key on the free plan. The adapter uses the regional host and will not reuse a US key on another region.
- **Adzuna.** `GET https://api.adzuna.com/v1/api/jobs/{country}/search/{page}` with `app_id` and `app_key`. The free tier is 25 requests/minute, 250/day, and 2,500/month. Personal job search and publishing listings are permitted with attribution; a commercial product is limited to a 14-day evaluation and needs a written licence after that. Adzuna does not cover the Philippines or the UAE, so PH/AE searches use Jooble, employer pages, and alerts.

Live calls still require the operator to set `SEARCH_TERMS_ACKNOWLEDGED=true` and provider keys. A block signal disables the source; it is never retried through another identity.
