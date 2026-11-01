# Phase 5: Job discovery engine v1: sources, company directory, normalization, dedupe

**Status:** Done · **Release:** R1 · **Depends on:** 4 · **Features:** F4 · **Reference:** [`research/02`](../research/02-job-discovery-and-site-access.md)

## Goal

Reliably ingest a large, fresh, deduplicated pool of real open jobs worldwide from compliant sources, and link them to Tracks. Data quality matters more than raw count.

## Acceptance scenarios

1. "Run now" on a Track → progress view (boards checked, jobs found, new) → within minutes the Track has matched jobs (rough, rule-based link until Phase 6).
2. The same job posted on Greenhouse, Himalayas, and Jooble appears **once** with three source links; the apply URL is the Greenhouse one.
3. A job removed from its ATS is marked `closed` within one polling cycle and hidden from "open" views.
4. Admin source-health page: per adapter success rate, latency, jobs/day, last error, block signals; a failing adapter trips its circuit breaker and alerts.
5. Paste a company careers URL → ATS detected → board added to the directory → jobs ingested.

## Tasks

### Adapter framework (`packages/py-core/sources/`, skill `source-adapter`)
- [x] Interface: `discover(params) -> AsyncIterator[RawJob]`, `fetch_detail(ref)`, `health()`, metadata (`terms_note`, `rate_limit`, `auth`, `countries`, `layer`).
- [x] HTTP client: httpx with descriptive UA + contact URL, per-host DBOS queue (concurrency + rate limit), retries with jitter, conditional requests (ETag/Last-Modified), response caching, circuit breaker, block-signal detector (429/403 bursts, challenge pages, auth walls) ⇒ disable + alert (never evade).
- [x] Fixtures: recorded responses per adapter for tests (no live calls in CI).

### Layer 1 adapters (ATS)
- [x] Greenhouse, Lever (+EU), Ashby, Workable, SmartRecruiters, Recruitee. Port mapping logic from `kame-hunt/src/sources/ats.ts`.
- [ ] Deferred (later phase): Personio, Workday (cxs JSON), BambooHR, Breezy.

### Layer 2 adapters (boards)
- [x] Remotive, Remote OK, Himalayas, Arbeitnow, Jobicy, The Muse. Keys stored as platform-level secrets (app config) with per-source quotas shared across tenants.
- [ ] Deferred (later phase): HN Who's Hiring, We Work Remotely RSS, USAJobs, Adzuna, Jooble, Careerjet, Reed.

### Layer 3 (generic career pages)
- [x] JSON-LD `JobPosting` extractor (extruct) + sitemap discovery + robots.txt compliance; Playwright render only on demand for JS-only pages (rate-limited, low priority).

### Company directory
- [x] `companies`, `company_boards`; ATS URL detector (regex per ATS) + slug validator; Common Crawl CDX importer (monthly DBOS workflow, batched, resumable); link mining from ingested apply URLs; user "add careers page"; health checks + deactivation; poll tiers (hot/warm/cold) driven by recent Track matches.
- [x] Company enrichment (free): domain from board, name normalization, favicon, size/industry when the source provides it.

### Normalization & dedupe
- [x] Normalizer to canonical `jobs` schema: HTML sanitize (bleach/nh3), text, title normalization (Phase 4), occupation codes, seniority (rules + LLM fallback batched), employment type, work mode, locations (geocode), remote eligibility (structured fields first; LLM extraction from text with quotes for evidence), salary parse (regex + LLM fallback; currency/period normalized), skills (taxonomy), language detection, posted/expiry dates.
- [x] Dedupe: exact external id; fuzzy (company + normalized title + location + SimHash on description) with thresholds tuned on a labeled sample; merge into `job_sources`; canonical apply URL preference (company ATS > company site > board).
- [x] Repost/age tracking; closed detection by absence on next poll (two consecutive misses) or 404 on detail.
- [ ] Retention: closed jobs' full text compressed after 90 days; keep minimal metadata for history/insights. (deferred; closed detection ships without compression)

### Track linking (interim)
- [x] `discover_track` workflow: Track sources (default: all Layer 1 directory + Layer 2 relevant to countries) → candidate jobs via compiled SQL filters + full-text → `track_jobs(status=new)`.
- [x] Track "Sources" tab: enable/disable per source, per-source params, coverage note for the Track's countries (`country_source_registry`).

### Frontend
- [x] Run-now progress (SSE): counts by stage.
- [x] Sources tab; admin source-health page; "add careers page" dialog.

## Edge cases & failure modes

- Source schema changes → adapter contract tests fail on fresh fixtures; health page shows parse-error rate; adapters fail closed (skip bad records, never crash the run).
- Massive boards (10k+ jobs) → streaming upserts, batched commits, idempotent keys.
- Duplicate companies with different names ("Meta", "Facebook") → alias table; merge tool in admin.
- Location strings like "Remote - US only" vs "Remote (Anywhere)" → eligibility parser with tests per pattern; unclear stays `unclear` (never guessed as eligible).
- Salary ambiguity ("100-120k" no currency) → infer currency from location only with low confidence flag.
- Time zones and dates: store UTC; "posted 3 days ago" relative strings converted at fetch time.
- Board API quota exhaustion (Adzuna/Jooble) → global scheduler spreads quota across tenants by priority; degrade gracefully.
- Legal/terms: each adapter's `terms_note` reviewed; attribution where required (Remote OK, Remotive).

## Testing

- Adapter fixture tests; normalizer unit tests (salary, eligibility, seniority patterns ≥ 100 cases); dedupe precision/recall on a labeled set of ≥ 300 pairs (target precision ≥ 98%, recall ≥ 90%); workflow test for `discover_track` with fake adapters; load test: 50k jobs ingest on the VM spec.

## Docs to update

`docs/architecture/job-discovery.md` (new), `research/02` catalog (verified status per source), skill `source-adapter`.

## Exit criteria

- [x] Scenarios 1–5 pass; ≥ 10 adapters live and healthy; directory ≥ 5,000 validated boards; dedupe targets met.
