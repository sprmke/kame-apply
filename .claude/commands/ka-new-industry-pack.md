# ka-new-industry-pack

Add a curated industry pack for `$ARGUMENTS` (for example `hospitality`, `healthcare`, `trades`).

1. Read the `industry-pack` skill, `docs/architecture/industries.md`, and the program plan §4–§5.
2. Create `apps/api/app/industries/packs/<key>.py` from the closest existing pack, then register
   it in `registry.py` and the template map.
3. Fill role families, UI states/groups, facets, criteria defaults, ladder, credentials, answer
   keys, sources, matching, profile, resume, AI brief, safety, and features.
4. Add every label key to `apps/web/i18n/locales/en.json`.
5. Add manifest + validation tests in `apps/api/tests/test_industries.py`.
6. Update `docs/architecture/industries.md`, the program plan, and affected route guides.
7. Run `uv run pytest apps/api/tests/test_industries.py -q`, `pnpm run format:check`,
   `pnpm run type-check`, and `pnpm run check:industry-branches` when it exists (IND-2).

The PR must contain **no component or router diff** except i18n and docs. If a page needs a new
control, change the schema and General first, then the pack selects it.
