---
name: source-adapter
description: "How to add a job source adapter (API, feed, board, career page): interface, normalization, terms note, rate limits, fixtures, health metrics, tests. Phase 5."
---

# Source adapter

Read `docs/phases/phase-05-job-discovery.md`, `docs/research/02-job-discovery-and-site-access.md`, and `.cursor/rules/job-site-access.mdc` first.

1. **Pick the layer** (official ATS API > public board API/feed > career page structured data > email alert > extension clip > opt-in personal-mode). Prefer the highest layer that works.
2. **Terms note** in the adapter docstring: URL of the terms/API docs, what is allowed, attribution requirements, review date. No terms review ⇒ no adapter.
3. **Interface**: `fetch(cursor) -> RawPostings`, `normalize(raw) -> JobCandidate`, `health() -> SourceHealth`. Pure functions for normalize; network only in fetch.
4. **Politeness**: descriptive User-Agent with contact URL, per-host DBOS queue (concurrency + rate), conditional requests/ETag, backoff, circuit breaker, robots.txt for HTML. A block signal disables the source and alerts. Never add evasion.
5. **Normalization**: map to the canonical `jobs` schema (company resolution, title normalization, location, salary to USD/month, work mode, content hash). Keep source ids and canonical URL for dedupe.
6. **Fixtures**: recorded real responses (scrubbed) under `apps/api/tests/fixtures/sources/<name>/`; tests assert normalize output and edge cases (missing salary, remote-only, closed jobs).
7. **Health metrics**: last success, items fetched, error rate, block signals, freshness; shown in the Sources view.
8. **Register** the adapter, add it to the source catalog doc, and note rate-limit settings.
