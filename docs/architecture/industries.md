# Industries and packs (IND program)

An **industry pack** is one versioned, code-reviewed description of how the app behaves for a
field of work. Discovery, criteria, matching, profile, answers, resume, AI prompts, safety, and UI
visibility read the pack. Components and routers never branch on an industry key.

Current packs: **General** (base layer, always available), **Technology** (encodes the behavior
the app shipped with), and **Hospitality and food** (kitchen roles first; front of house titles
only in v1). Adding a field later is a content PR: pack file, i18n strings, templates, fixtures,
evals.

## 1. Where the field lives

| Level | Storage | Meaning |
| --- | --- | --- |
| Workspace | `workspace_industries(workspace_id, industry_key, is_primary, custom_pack)` | The fields this workspace works in. Chosen at workspace creation, confirmed during onboarding (IND-2). Drives global pages. |
| Track (search) | `tracks.industry`, `tracks.industry_version` | One pack per search. Defaults to the workspace primary; can differ for a two-field person or a coach. |
| Profile | No industry column | Profile sections are the **union** of the workspace fields. A person can cook and code. |

`general` is always available to a track even when it is not a stored workspace industry. A
template whose industry has no curated pack yet maps its track to `general`.

Decisions: D1 = workspace default + per search; D2 = Philippines + UAE/Gulf for the first live
chef searches. See `docs/workflow/planned/multi-industry-support.md` §16.

## 2. Pack shape

Schema: `apps/api/app/industries/schema.py`. Curated packs:
`apps/api/app/industries/packs/{general,technology,hospitality}.py`.

| Field | What it drives |
| --- | --- |
| `key`, `version`, `label_key`, `icon` | Identity. Version is stored on a track for traceability. |
| `detection` | ISCO groups, ESCO prefixes, title keywords, resume cues (IND-9 classifier). |
| `role_families` | Second level of the workspace picker (`Kitchen`, `Data`, ...). |
| `ui` | Criteria groups and order, per-field state (`visible`, `collapsed`, `hidden`), profile section order, label overrides, nav flags. |
| `facets` | Industry dimensions (cuisine, station, kitchen type) with options, synonyms, scope, match mode. |
| `criteria_defaults` | Work modes, employment types, shifts, salary period, posting age. |
| `seniority_ladder` | Local rank names mapped onto the shared `Seniority` scale. |
| `credentials` | Named credentials, aliases, countries, validity, knockout weight. |
| `answer_keys` | Canonical answer keys a pack adds or hides. |
| `sources` | Adapters, Adzuna category per country, query templates, employer tags, alert sources. |
| `matching` | Score weights, generic title words, title equivalence groups. |
| `profile` | Section order, labels, gap questions/actions, evidence metric patterns, completeness items. |
| `resume` | Template id, section order, photo default, bullet guidance. |
| `ai` | Short brief (max 600 chars) and vocabulary injected into prompts. |
| `safety` | Extra scam signals. |
| `features` | Be Found, GitHub links, coding practice, portfolio images, resume photo, query sources. |

All models are frozen and `extra="forbid"`. Enums are shared with `tracks/criteria.py`, so a pack
cannot invent a new employment type or seniority level.

## 3. Resolution

`apps/api/app/industries/resolve.py`, pure functions:

- **Track page:** the track's pack with General underneath. Pack state overrides General.
- **Global page:** the union across the workspace's enabled packs. A field is hidden only when
  every enabled pack hides it. Visible beats collapsed beats hidden. Labels come from the primary
  pack first.
- **`general`** is the base layer, never a replacement. It is only a union member when the
  workspace has no stored field.
- **Hiding is UX only.** The API accepts every `CriteriaV1` field for every pack. A hidden field
  with a saved value is surfaced as "set earlier" in IND-2 so it never acts invisibly.
- The resolved manifest includes field states, ordered groups, labels, profile sections, nav,
  facets, features, the seniority ladder, and criteria defaults.

## 4. Criteria additions`CriteriaV1` gained additive optional fields (schema version stays 1):

| Field | Values |
| --- | --- |
| `shifts` | `morning`, `afternoon`, `evening`, `night`, `weekend`, `split`, `rotating` |
| `facets` | `dict[str, list[str] | bool | int]`, keys validated against the track's pack |
| `salary.includes` | `accommodation`, `meals`, `tips`, `service_charge`, `transport` |
| `employment_types` | added `casual`, `seasonal` |

`compile_filter` emits `shift_any` and `facets` predicates and carries `salary.includes` into the
salary predicate. Unknown facet keys or options return 422 with the field path.

## 4b. Hospitality pack

`packs/hospitality.py`:

- **Role families:** Kitchen, Pastry and bakery, Catering and banquets, Cruise and resort, Front of house (titles only).
- **Facets:** cuisine (14 options with synonyms), kitchen type, station, covers per service band.
- **Visible filters:** shifts, employment types including casual/seasonal, pay includes (accommodation, meals, tips, service charge, transport), commute radius, visa, relocation, posting age.
- **Hidden filters:** timezone overlap, education, clearance. They stay one tap away under Show all filters.
- **Ranks:** kitchen hand, commis, chef de partie, sous chef, head chef, executive chef mapped onto the shared seniority scale.
- **Credentials:** food handler, ServSafe Handler/Manager, HACCP, UK Food Hygiene L2/L3, TESDA Cookery NC II, RSA, STCW, culinary diploma, seaman's book. Names, aliases, countries, validity, knockout flag. Answer-bank wiring lands in IND-6.
- **Templates:** 15 kitchen starters in `taxonomy/seed.py` (chef, commis, chef de partie, sous, head, executive, pastry, baker, line, prep, grill, banquet, cruise, kitchen supervisor, catering). A Hospitality workspace sees these plus General; a Technology workspace does not.
- **Matching plan, profile plan, resume plan, AI brief, safety signals:** stored in the pack. Matching and prompt wiring land in IND-5/IND-7/IND-8.

## 4c. Web reading the packs

`apps/web/app/composables/useExperience.ts` loads `GET /workspace/experience` once per workspace and exposes `manifestFor(industry)`, `stateOf`, `labelOf`, `facetsFor`, `packLabel`, `facetLabel`, `optionLabel`. Pages never compare an industry key.

- Create workspace: two steps, then the chosen fields are written through the workspace industry API. The default Technology field is removed when the person chooses only another field, so a chef workspace does not inherit GitHub or remote filters.
- New search: field chips from enabled packs; templates filter by the selected field; `industry` is sent on create.
- Settings > General: Fields of work card with add, remove, make primary, and an inline consequence preview.
- Criteria: groups render from the pack. Visible fields inline, collapsed fields under More filters, hidden fields behind Show all filters, with a Set earlier line when a hidden field has a saved value.
- `pnpm run check:industry-branches` fails on `industry ===` / `pack.key ===` in `apps/web/app`; it runs in `ci:quality`.

## 4d. Discovery, matching, profile (IND-4 to IND-6)

- **Discovery:** `_boards_for_run` filters by `company_boards.industries` and the pack's `employer_tags`; a Track's explicit source toggles still win. Without toggles, the pack's `sources.adapters` are the allowlist. `sources/search_service.py` adds Layer 4 keyword + location search with a shared `source_query_cache`, `jobs/classify.py` fills `jobs.industry_hints`, `jobs.facets`, and a coarse occupation code, and `source_coverage` powers `GET /sources/coverage`. The Track page shows the coverage notice and a **Where we look** disclosure.
- **Matching:** default weights come from `pack.matching.weights`; title groups, generic words, credentials named in the posting, shift overlap, commute distance, facet filters, and facet boosts all use the pack. Credential, shift, and pay-include rows appear in the fit ledger.
- **Profile and answers:** `profile_facets` stores cuisine, station, and kitchen type as facts with evidence refs; the profile page adds or removes values. Answer keys are filtered by enabled packs (`packs`, `answer_keys.add`, `answer_keys.hide`). Portfolio images are accepted for `kind=portfolio` and re-encoded to strip EXIF/GPS.

## 4e. Advice, resume, AI assists, extra packs

- **Advice:** gap actions, `Get found` checklist, interview questions, and trial-shift checklist live on `pack.profile`. Safety fee signals live on `pack.safety` and the shared L1 rules. Salary advice carries posting period and pay includes.
- **Resume:** `build_from_profile` emits certifications, projects, and languages and orders sections by `pack.resume.section_order`; `section_titles` renames headings. `create_base` records the pack template id. `profile_extract` v2 and the resume/critique/cover-letter prompts receive the pack brief at runtime.
- **AI assists:** `POST /industries/detect`, `POST /tracks/plan`, `POST /industries/draft`, `POST /workspace/industries/custom`, and `GET /sources/advice` are deterministic baselines. The AI prompt entries exist; no endpoint blocks on a model.
- **Extra packs:** Healthcare, Engineering, Skilled trades, Customer service and retail, Education, Logistics and driving, Finance and accounting, Admin and virtual assistance, Sales and marketing, Creative and design. Each is content-only: role families, detection, credentials, matching weights, profile/advice content, resume order, AI brief, source plan.

## 5. HTTP

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/v1/industries` | Curated packs: key, label, icon, role families. Any authenticated user. |
| POST | `/api/v1/industries/detect` | Deterministic field detection from a title or description. |
| POST | `/api/v1/industries/draft` | Deterministic custom pack draft; user-scoped. |
| POST | `/api/v1/workspace/industries/custom` | Accept a custom pack draft. Body: `key`, `description`, optional `base_pack`, optional `is_primary`. The server re-derives the pack from the description; owner/admin; audited. |
| GET | `/api/v1/workspace/industries` | The active workspace's fields plus General (always last). |
| POST | `/api/v1/workspace/industries` | Add a field. `workspace.update` (owner/admin). |
| PUT | `/api/v1/workspace/industries/primary` | Change the primary field. owner/admin. |
| DELETE | `/api/v1/workspace/industries/{key}` | Remove a field. Tracks move to the remaining primary or General. owner/admin. |
| GET | `/api/v1/workspace/experience` | Resolved global manifest plus one manifest per enabled pack. |
| GET | `/api/v1/workspaces/{id}/experience` | Same, but the path id must equal the verified active workspace or 404. |
| POST | `/api/v1/tracks/plan` | Pack-aware deterministic search plan and source queries. |
| GET | `/api/v1/sources/advice` | Coverage plus alert/employer suggestions for a field and country. |

Track create/update accepts `industry`. A value must be General or one of the workspace's fields
(422 otherwise). Omitting it uses the template's pack when curated, else the workspace primary.

Audit actions: `workspace.industry_added`, `workspace.industry_removed`,
`workspace.industry_primary_changed`, `workspace.custom_pack_accepted`,
`track.industry_changed`, `track_source.defaulted`.

## 6. Data and migration

- `workspace_industries`: tenant table with forced RLS and a partial unique index that allows one
  `is_primary` row per workspace. Cross-tenant test in `apps/api/tests/test_industries.py`. It is
  included in the workspace JSON export.
- `tracks.industry` defaults to `technology`; `industry_version` records the pack version.
- Migration `0040` backfills Technology as primary for every live workspace and maps tracks to
  their template's pack when it exists, otherwise General. Backfill notes:
  [`deployment.md`](./deployment.md) §2.

## 7. Tests

`apps/api/tests/test_industries.py`:

- every pack has a state and a group for every criteria field;
- the Technology manifest snapshot (shifts and facets hidden, tech-stack label, current weights);
- union rules across General and Technology;
- workspace fields, experience manifest, and path-scoped experience;
- RBAC on workspace field changes;
- removal reassigns tracks and falls back to General;
- chef template intake in General until IND-3;
- track industry and facet validation;
- `workspace_industries` RLS isolation.

## 8. Roadmap

| Slice | Status |
| --- | --- |
| IND-0 decisions and source verification | Decisions recorded; source terms verification runs with IND-4 |
| IND-1 pack foundation | Shipped |
| IND-2 picker and visibility | Shipped (workspace picker, Fields of work, useExperience, pack-driven criteria, Show all, branch check) |
| IND-3 hospitality content | Shipped (pack, 15 templates, i18n, manifest tests) |
| IND-4 discovery for non-tech | Shipped (search adapters, cache, classification, coverage, Where we look) |
| IND-5 matching | Shipped (pack weights, credentials, shifts, facets, commute, ledger rows) |
| IND-6 profile and answers | Shipped (profile facets, filtered answer keys, portfolio images) |
| IND-7 resume, tailor, letters | Shipped (pack sections/order, prompt v2 brief) |
| IND-8 advice, safety, interview | Shipped (gaps, Get found, interview, fee signals, salary includes) |
| IND-9 AI assists | Shipped (deterministic detection, search plan, custom pack draft, source advice) |
| IND-10 more packs | Shipped (Healthcare, Engineering, Trades, Customer service, Education, Logistics, Finance, Admin, Sales/Marketing, Creative) |
