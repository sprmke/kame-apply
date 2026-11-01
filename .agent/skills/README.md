# Agent skills

Canonical skills live here and are symlinked into `.claude/skills/` and `.cursor/skills/` by `pnpm run setup:ai-tooling`. OpenCode reads this directory directly (`opencode.json`).

## Core (ported and adapted)

`fastapi-stack` · `fastapi-jwt-auth` · `rbac-and-audit` · `audit-logging` · `alembic-migrations` · `fix-migration-issues` · `pgvector-search` · `pdf-generation` · `workspace-scoping` · `documentation-maintenance` · `route-guides` · `docs-first` · `self-review` · `git-commits` · `human-copy` · `minimal-ui-copy` · `accessibility` · `karpathy-guidelines` · `workflow` · `design-review`

## Domain (initial versions; each refined in the phase that uses it)

`source-adapter` (P5) · `ats-adapter` (P13/15) · `dbos-workflows` · `pydantic-ai-features` · `ai-evals` · `wxt-extension` (P13) · `live-view` (P16)

## Frontend (Vue / Nuxt / Field Notes, written fresh)

`vue-query-data` · `vee-validate-forms` · `tanstack-table-vue` · `field-notes-components`

## Deferred to their phase

`gmail-listener`/inbound email (Phase 17), `production-readiness-review` (Phase 14), the Claude Agent Bridge skills (Phase 12b).

## External skills

Installed with `npx skills add`, read in full before committing, pinned in `skills-lock.json`, with the reason recorded below. None are installed yet; the plan is in `docs/research/06-agentic-workflow.md` §2. Do not install React-specific skills. Superpowers stays opt-in.

| Skill | Source | Why | Pinned |
| --- | --- | --- | --- |
