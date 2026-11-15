---
name: industry-pack
description: Add or change an industry pack so a new field of work (hospitality, healthcare, trades) works end to end without touching components or routers. Use for IND-3, IND-10, or any new curated field.
---

# Industry pack

A pack is content, not a branch. Read `docs/architecture/industries.md` and
`docs/workflow/planned/multi-industry-support.md` §4–§5 before editing.

## Rules

1. **No component or router changes.** Pages read the resolved manifest. No `industry ===`,
   `pack.key ===`, or pack-specific component in `apps/web/**` or an API router.
2. **Hide, never delete.** A pack can move a control to `hidden`. Saved values stay and the API
   still accepts them. Hidden fields with values are shown as "set earlier" (IND-2).
3. **Schema is closed.** Reuse existing field ids, `Seniority`, `EmploymentType`, `Shift`, and
   facet kinds. A pack cannot add a new field type or weaken a P-rule.
4. **Facts stay facts.** Pack AI briefs guide wording only. No invented credentials, cuisines, or
   metrics.
5. **Sources follow P2/P5.** A pack lists adapters that already passed their terms check. It never
   adds evasion or a logged-in scrape.

## Steps

1. Copy the closest pack in `apps/api/app/industries/packs/` and set `key`, `version: 1`,
   `label_key`, `icon`.
2. `detection`: ISCO groups, ESCO prefixes, title keywords, resume cues.
3. `role_families`: the second level a person recognizes (Kitchen, Pastry, Front of house).
4. `ui`: a `states` patch over General. Mark every field `visible`, `collapsed`, or `hidden`.
   Add a group for the pack's facets when the field id is also a facet id.
5. `facets`: options with synonyms, `applies_to`, match mode. Every option needs a label key.
6. `criteria_defaults`, `seniority_ladder`, `credentials`, `answer_keys`.
7. `sources`, `matching`, `profile`, `resume`, `ai`, `safety`, `features`.
8. Register the pack in `apps/api/app/industries/registry.py` (`PACKS` and the template map).
9. Add every `label_key` to `apps/web/i18n/locales/en.json`.
10. Add fit-ledger labels, templates, and fixtures from real, synthetic postings.
11. Add a manifest snapshot test and pack validation test in `apps/api/tests/test_industries.py`.
12. Update `docs/architecture/industries.md`, the phase/program plan, and any route guide whose
    labels changed.

## Checks

```bash
uv run pytest apps/api/tests/test_industries.py -q
pnpm run check:filenames && pnpm run format:check
pnpm run type-check
```

- Every criteria field has one state and one group (registry test).
- Every i18n key resolves.
- Every credential/answer key/adapter/template exists.
- No new field type, no safety change, no `industry ===` branch.
- Server tests still prove wrong-`app.workspace_id` reads return 0 rows.
