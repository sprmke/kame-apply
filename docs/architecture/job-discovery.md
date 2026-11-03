# Job discovery (Phase 5)

Ingest open jobs from compliant sources into a global pool, dedupe them, and link matches to Tracks.

## Layers

| Layer | Adapters (v1) |
| --- | --- |
| 1 ATS | greenhouse, lever, ashby, workable, smartrecruiters, recruitee |
| 2 boards | remotive, remoteok, himalayas, arbeitnow, jobicy, muse |
| 3 career pages | career_jsonld (JobPosting JSON-LD) |

Adapter package: `packages/py-core/kame_core/sources/`. Each adapter carries a terms note, descriptive UA, and fails closed on block signals (never evasion). Career-page crawling checks `robots.txt` first (`robots_allowed`, cached per host for an hour) and raises a block signal on a disallow. Conditional requests (ETag/Last-Modified) are supported by the HTTP client but not yet wired into the board poller.

## Data model

**Global (no RLS):** `sources`, `companies`, `company_boards`, `jobs`, `job_sources`, `country_source_registry`.

**Tenant (RLS):** `track_sources`, `track_jobs`, `discovery_runs`.

Apply URL preference: company ATS > career page > board (`jobs/dedupe.py`). Dedupe requires company + normalized title + location compatibility + SimHash distance ≤ 8, so two requisitions in different cities do not merge. One bad record rolls back to a savepoint, not the whole run; a failed run is persisted with `status=failed`.

Closed detection: two consecutive poll misses on a board/source → `jobs.status=closed`. Applied to ATS/board sources and to the Layer-2 feeds (Remotive, RemoteOK, Arbeitnow, Jobicy, Muse, Himalayas).

## Directory

Directory seed: 64 curated boards (status `active`, validated) plus generated candidate slugs (status `candidate`, `validation_method=seed_unverified`). Only active, validated boards are polled; candidates exist so the directory can grow once a board is confirmed. `GET /sources/directory/stats` reports `boards_active` and `boards_candidate` separately.

Monthly CDX import: `scripts/sources/refresh_directory.py --cdx-jsonl …`.

User add: `POST /api/v1/sources/careers` with a careers URL (ATS detector).

## Workflows

`POST /api/v1/tracks/{id}/discover` runs `discover_track` (service + optional DBOS enqueue when `DBOS_SYSTEM_DATABASE_URL` is set). Progress on the run row; SSE at `/api/v1/discovery-runs/{id}/events`.

Interim Track link: rule filter on criteria titles/skills/work modes (`sources/discover.py`). Phase 6 replaces this with ranking.

## Admin

`GET /api/v1/sources/health` (managers): success/error counts, latency, circuit, block signals.

UI: `/settings/sources`, Track settings Sources toggles, Track detail **Run now**.

## Fixtures

Recorded responses under `apps/api/tests/fixtures/sources/<adapter>/` (CI never calls live boards).
