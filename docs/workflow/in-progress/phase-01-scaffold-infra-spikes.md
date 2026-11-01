# Phase 1: Monorepo scaffold, local infra, CI, spikes (scratchpad)

**Branch:** `phase/01-scaffold` · **Started:** 2026-10-28 · **Phase file:** `docs/phases/phase-01-scaffold-infra-spikes.md`

## Plan (vertical slices)

1. [x] A. Python workspace + `apps/api` (factory, settings, health, logging, error envelope) + Postgres/MinIO/Mailpit compose + Alembic first migration + pytest
2. [x] B. Web: Nuxt 4 + `packages/ui` + Hey API client generation + Vitest
3. [x] C. Root scripts, `dev.sh`, CI workflow, drift check, docs
4. [x] D. Local spikes: DBOS, RenderCV, fastembed, Hey API+Vue Query, WXT+ui
5. [ ] E. (blocked on owner) Cloud-only spikes (Oracle A1, CDP over internet): need the user's accounts; documented as pending

## Decisions

- Ports: web 3100, api 8100, postgres 5442, minio 9100/9101, mailpit 8125/1125 (avoid clashes with other Kame apps).

## Open questions

- Oracle account and a public host for the CDP spike are required from the user.
