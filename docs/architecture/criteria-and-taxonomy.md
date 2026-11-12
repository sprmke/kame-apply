# Criteria and taxonomy (Phase 4)

## CriteriaV1

One JSON document is the source of truth for a Track's search. Shape: `apps/api/app/tracks/criteria.py`. Empty fields mean "any". Soft requirement: at least one title or occupation (or NL text on create).

| Concern | Module |
| --- | --- |
| Schema | `tracks/criteria.py` |
| Summary sentence | `tracks/summary.py` (deterministic) |
| Diff / merge / invent-guard | `tracks/diff.py`, `merge.py`, `invent_guard.py` |
| NL compile | `tracks/compile_nl.py` (`criteria_compile.v1`, PromptedOutput) |
| Search plan | `tracks/plan.py` (`search_plan.v1`; role-typical titles, skills, filters) |
| Compiled predicates | `tracks/compile_filter.py` (versioned JSON for Phase 6; no raw SQL) |
| Validate | `tracks/validate.py` (warnings, keyword boolean syntax) |
| FX / period | `tracks/currency.py` + `currency_rates` table |
| Geocode | `tracks/geocode.py` + `geocode_cache` (Nominatim, 1 req/s, UA) |

`track_criteria.version` increments on every structured write. Preview count stays "Preview available after first discovery" until Phase 5.

## Search plan (defaults + AI)

A new search should work before the user touches a filter. `POST /tracks/plan` and `POST /tracks/{id}/criteria/suggest` return a full plan:

- **Role-shaped fields** come from the plan: titles and synonyms, must/nice skills, seniority, employment types, work modes, remote regions, posting age, agency exclusion.
- **Personal filters** stay as the user set them on refine: locations, countries, timezone base, salary, company lists, caps, visa, relocation, match floor. A field is only replaced when the description mentions it (visa, relocation, freshness, agencies, region, work mode).
- **Deterministic baseline** always exists: title from the first role phrase, nearest curated template for skills, parsed work modes/employment/seniority, `exclude_agencies=true`, `posting_max_age_days=21`, 7 for "last week" and 30 for "last month".
- **AI is optional.** No key, budget stop, or provider error falls back to the baseline and returns `source="defaults"` + `ai_error`, never a failed search (P7). The plan is a suggestion until the user accepts it.
- **Safety.** The description is delimited untrusted data, the call is tool-less (P6), and the model may not propose salary, visa, cities, companies, education, or clearance. Those stay user-owned.

`Create` with `suggest: true` plans before insert, so a text-created Track lands with usable titles and skills. `duplicate` keeps the stored criteria untouched.

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
| GET/POST | `/api/v1/tracks` | list / create |
| GET | `/api/v1/tracks/templates` | global templates |
| POST | `/api/v1/tracks/reorder` | active Tracks only |
| GET/PATCH | `/api/v1/tracks/{id}` | detail / metadata |
| PUT | `/api/v1/tracks/{id}/criteria` | structured replace |
| POST | `/api/v1/tracks/{id}/criteria/compile` | NL → patch (+ optional apply) |
| POST | `/api/v1/tracks/plan` | Full search plan for a role text, nothing saved |
| POST | `/api/v1/tracks/{id}/criteria/suggest` | Plan merged into a Track (`apply` optional) |
| POST | `/api/v1/tracks/{id}/duplicate` \| `/archive` | |
| GET | `/api/v1/tracks/geo/lookup?place=` | Nominatim via cache |
| GET | `/api/v1/taxonomy/occupations/normalize` | |
| GET | `/api/v1/taxonomy/skills/normalize` | |

Audit actions: `track.created`, `track.updated`, `track.criteria_updated`, `track.duplicated`, `track.archived`, `track.reordered`.

## Evals

`apps/api/tests/evals/fixtures/criteria/` (≥60 descriptions). Offline: merge + invent-guard + title accuracy ≥90%. Live LLM: inject `run_structured` or `RUN_LIVE_AI=1` when quota allows.

Search plan: `apps/api/tests/evals/test_search_plan_eval.py` runs the deterministic baseline over every fixture (role signal present, real filters, no invented salary/visa/location) plus English title accuracy ≥85%. The AI path is covered by `tests/test_tracks.py` with an injected runner.
