# Phase 1: Monorepo scaffold, local infra, CI, technical spikes

**Status:** Done · **Release:** Foundation · **Depends on:** 0 · **Unlocks:** 2

## Goal

A running skeleton: `pnpm run dev` starts web + api + Postgres + MinIO; CI is green; the riskiest stack assumptions are proven by spikes before any feature depends on them.

## Tasks

### Monorepo
- [x] pnpm workspaces + Turborepo: `apps/web`, `apps/api`, `apps/runner` (empty shell), `apps/extension` (empty shell), `packages/ui`, `packages/api-client`, `packages/py-core`.
- [x] uv workspace for Python (`apps/api`, `apps/runner`, `packages/py-core`), Python 3.13, ruff, basedpyright, pytest + pytest-asyncio + httpx.
- [x] `apps/api`: FastAPI app factory, settings (pydantic-settings), health endpoints (`/healthz`, `/readyz` with DB check), structured logging (JSON, request id), Sentry init (env-gated), CORS, error envelope (`{error:{code,message,details}}`), `/api/v1` router.
- [x] SQLAlchemy 2 async + Alembic (first migration: extensions `pgvector`, `pg_trgm`, `citext`; `activity_log` table).
- [x] `apps/web`: Nuxt 4 + Vue 3.5 + TS strict (`ssr: false` for app routes, prerender for public pages), Tailwind v4, Reka UI, `@nuxt/icon` (Phosphor), `@nuxtjs/i18n`, `@nuxt/fonts`, Pinia, TanStack Vue Query, `@nuxt/eslint`; `packages/ui` as a Vue component library consumed by web (and later the extension); Hey API `openapi-ts` generating `packages/api-client` from the API OpenAPI.
- [x] `infra/docker-compose.dev.yml`: Postgres 17 + pgvector, MinIO, Mailpit. `./dev.sh` runs all.
- [x] Scripts: `dev`, `dev:api`, `dev:web`, `db:migrate`, `db:migrate:new`, `db:reset:local`, `db:seed`, `lint`, `format`, `type-check`, `test`, `build`, `gen:api-client`, `ci:quality`.

### CI (GitHub Actions)
- [x] Jobs: lint+format check, type-check (TS + basedpyright), tests (pytest with Postgres service, Vitest), build, `check:filenames`, `check:ai-tooling-sync`, stack-terminology scan, OpenAPI client drift check (generated client must be committed and up to date).
- [x] CI creates RLS app role via `scripts/dev/ci-prepare-postgres.sh` before pytest.

### Spikes (each produces a short note in `docs/architecture/spikes/` + keep/drop decision)
- [x] **DBOS:** Keep. See `docs/architecture/spikes/01-dbos.md`.
- [x] **Oracle Always Free:** Keep (primary); Hetzner CAX11 fallback; live A1 provision = operator. See `docs/architecture/spikes/02-oracle-always-free.md`.
- [x] **RenderCV/Typst:** Keep. See `03-rendercv-typst.md`.
- [x] **CDP screencast:** Keep (localhost proven; internet leg on first host). See `04-cdp-screencast.md`.
- [x] **fastembed** on ARM: Keep (re-time on first host). See `05-fastembed.md`.
- [x] **Hey API + FastAPI + Vue Query:** Keep. See `06-hey-api-vue-query.md`.
- [x] **WXT + Vue + `packages/ui`:** Keep. See `07-wxt-vue-ui.md`.

## Edge cases

- ARM (Oracle A1) image compatibility: Playwright Chromium on arm64, fastembed ONNX on arm64, Typst binary on arm64 (spikes verify).
- Pin Python and Node versions (`.python-version`, `.nvmrc`/`packageManager`).

## Testing

- [x] `pytest` smoke (health, DB migration up/down), Vitest smoke, CI green.

## Docs to update

`tech-stack.md` (spike outcomes), `CLAUDE.md` commands section (now real), `docs/architecture/deployment.md` (new: local + VM layout).

## Exit criteria

- [x] Fresh clone → `pnpm install && pnpm run dev:docker && pnpm run dev` works per README.
- [x] CI green on a PR (GitHub Actions) — [PR #1](https://github.com/sprmke/kame-apply/pull/1) all jobs green.
- [x] All seven spikes have a decision recorded; any "drop" updated in `tech-stack.md`.

## Implementation notes

Operator follow-ups (not eng blockers): first Oracle A1 (or Hetzner) bring-up with `applywave`; re-time fastembed/CDP on that host (checklist in spike 02). See [`REMAINING.md`](./REMAINING.md).
