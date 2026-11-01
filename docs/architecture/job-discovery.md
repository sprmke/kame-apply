# Job discovery (Phase 5)

Ingest open jobs from compliant sources into a global pool, dedupe them, and link matches to Tracks.

## Layers

| Layer | Adapters (v1) |
| --- | --- |
| 1 ATS | greenhouse, lever, ashby, workable, smartrecruiters, recruitee |
| 2 boards | remotive, remoteok, himalayas, arbeitnow, jobicy, muse |
| 3 career pages | career_jsonld (JobPosting JSON-LD) |

Adapter package: `packages/py-core/kame_core/sources/`. Each adapter carries a terms note, descriptive UA, and fails closed on block signals (never evasion).

## Data model

**Global (no RLS):** `sources`, `companies`, `company_boards`, `jobs`, `job_sources`, `country_source_registry`.

**Tenant (RLS):** `track_sources`, `track_jobs`, `discovery_runs`.

Apply URL preference: company ATS > career page > board (`jobs/dedupe.py`).

Closed detection: two consecutive poll misses on a board/source → `jobs.status=closed`.

## Directory

Seed ≥ 5,000 active boards: `pnpm run db:seed` or `uv run python scripts/sources/refresh_directory.py --seed`.

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
