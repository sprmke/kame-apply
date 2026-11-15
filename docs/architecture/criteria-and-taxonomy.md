# Criteria and taxonomy (Phase 4)

## CriteriaV1

One JSON document is the source of truth for a Track's search. Shape: `apps/api/app/tracks/criteria.py`. Empty fields mean "any". Soft requirement: at least one title or occupation (or NL text on create).

| Concern | Module |
| --- | --- |
| Schema | `tracks/criteria.py` |
| Summary sentence | `tracks/summary.py` (deterministic) |
| Diff / merge / invent-guard | `tracks/diff.py`, `merge.py`, `invent_guard.py` |
| NL compile | `tracks/compile_nl.py` (`criteria_compile.v1`, PromptedOutput) |
| Compiled predicates | `tracks/compile_filter.py` (versioned JSON for Phase 6; no raw SQL) |
| Validate | `tracks/validate.py` (warnings, keyword boolean syntax) |
| FX / period | `tracks/currency.py` + `currency_rates` table |
| Geocode | `tracks/geocode.py` + `geocode_cache` (Nominatim, 1 req/s, UA) |
| Industry pack | `industries/` (schema, packs, resolver). Details: [`industries.md`](./industries.md) |

`track_criteria.version` increments on every structured write. Preview count stays "Preview available after first discovery" until Phase 5.

### Industry-aware fields (IND-1)

These are additive and optional, so existing criteria documents stay valid (`schema_version` 1).

| Field | Shape | Notes |
| --- | --- | --- |
| `shifts` | `list[Shift]` | `morning`, `afternoon`, `evening`, `night`, `weekend`, `split`, `rotating`. Common outside tech. |
| `facets` | `dict[str, list[str] | bool | int]` | Keys exist in the Track's industry pack; unknown keys return 422. |
| `salary.includes` | `list[SalaryInclude]` | `accommodation`, `meals`, `tips`, `service_charge`, `transport`. |
| `employment_types` | added `casual`, `seasonal` | AU/NZ/UK hospitality and cruise work. |

`track_templates.industry` maps to a curated pack when one exists (`technology`), otherwise the
track starts in `general` until its pack ships.

## Taxonomy (global)

Tables (no RLS; app role SELECT-only except `geocode_cache` INSERT):

- `taxonomy_occupations` / `taxonomy_skills` (ESCO + O*NET codes, labels, alt titles, `vector(384)` for refresh jobs)
- `taxonomy_occupation_skills`, `taxonomy_crosswalks`, `taxonomy_aliases`
- `track_templates` (40+ curated starters)
- `currency_rates`

Curated seed + templates: `pnpm run db:seed` → `scripts/taxonomy/refresh.py --seed --fx`.

Full dumps: `uv run python scripts/taxonomy/refresh.py --esco-dir … --onet-dir …` (see script docstring for download URLs).

Normalizers: trigram + aliases on the request path (`taxonomy/normalize.py`); optional LLM tiebreak later. `POST /taxonomy/profiles/{id}/skills/backfill` links `profile_skills.skill_id`.

## HTTP

| Method | Path | Notes |
| --- | --- | --- |
| GET/POST | `/api/v1/tracks` | list / create (`industry` optional; defaults to the workspace primary) |
| GET | `/api/v1/tracks/templates` | global templates |
| POST | `/api/v1/tracks/plan` | pack-aware deterministic search plan |
| POST | `/api/v1/tracks/reorder` | active Tracks only |
| GET/PATCH | `/api/v1/tracks/{id}` | detail / metadata (`industry` change audited) |
| PUT | `/api/v1/tracks/{id}/criteria` | structured replace |
| POST | `/api/v1/tracks/{id}/criteria/compile` | NL → patch (+ optional apply) |
| POST | `/api/v1/tracks/{id}/duplicate` \| `/archive` | |
| GET | `/api/v1/tracks/geo/lookup?place=` | Nominatim via cache |
| GET | `/api/v1/taxonomy/occupations/normalize` | |
| GET | `/api/v1/taxonomy/skills/normalize` | |

Audit actions: `track.created`, `track.updated`, `track.criteria_updated`, `track.duplicated`, `track.archived`, `track.reordered`, `track.industry_changed`.

## Evals

`apps/api/tests/evals/fixtures/criteria/` (≥60 descriptions). Offline: merge + invent-guard + title accuracy ≥90%. Live LLM: inject `run_structured` or `RUN_LIVE_AI=1` when quota allows.
