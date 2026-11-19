# IND-1: Pack foundation (scratchpad)

**Branch:** `ind/01-pack-foundation` · **Started:** 2026-11-12 · **Plan:** `docs/workflow/done/multi-industry-support.md`

## Decisions recorded in IND-0

- **D1: workspace default + per search.** `workspace_industries` holds the fields a workspace works in; `tracks.industry` picks one per search.
- **D2: Philippines + UAE/Gulf** for the first live chef searches. IND-4 sources target PH and AE first.
- D3 front of house later, D4 platform-level keys, D5 web discovery off by default, D6 per-vendor terms check, D7 new phase file (IND program), D8 start IND now.

## Plan (vertical slices)

1. [x] Criteria core fields: `shifts`, `facets`, `salary.includes`, `casual`/`seasonal`.
2. [x] `industries/` package: schema, General + Technology packs, registry, resolver.
3. [x] `workspace_industries` table + RLS + backfill of `tracks.industry`.
4. [x] API: `GET /industries`, `GET /workspace/experience` and `/workspaces/{id}/experience`; workspace industry CRUD with RBAC + audit.
5. [x] Track create/read validates and defaults the industry.
6. [x] Tests: pack registry, resolver snapshot for Technology, RLS cross-tenant, API, track default.
7. [x] Docs: `docs/architecture/industries.md`, criteria, deployment, PRD note, plan status.
8. [x] IND-0 tooling: `industry-pack` skill, `industry-packs.mdc` rule, `/ka-new-industry-pack` command, sync.

## Follow-ups before the next slice

- Migration `0039` is included on this branch, so `0040` and `0041` form one head.
- IND-2 added the picker, `useExperience`, and `check:industry-branches`; workspace creation now
  defaults to Technology only when the person skips the field step.
- IND-3 adds the Hospitality pack; the add-field endpoint is already wired and returns 422 for
  unknown keys until that pack exists.

## Open questions

- Hospitality content and the picker UI land in IND-2/IND-3. IND-1 keeps the technology experience byte-for-byte.

## Decisions

- New workspaces get `technology` as primary until the IND-2 picker exists. Skipping the picker will set `general` then.
- `general` is always available to tracks even when it is not a stored workspace industry.
- A template whose industry has no curated pack yet maps its track to `general`.
- Track industry changes do not rewrite criteria; hidden fields keep their saved values.

## Verification log

- [x] `uv run pytest apps/api -q` (566 passed, 3 skipped)
- [x] `pnpm run lint` / `format:check` / `type-check`
- [x] `pnpm run check:api-client`
- [x] Cross-tenant test for `workspace_industries`
- [x] `pnpm run ci:quality` (final, isolated test DB)
