# Phase 4: Tracks & criteria builder + occupation/skills taxonomy

**Status:** Done · **Release:** R1 · **Depends on:** 3 · **Features:** F2, F3 · **Reference:** [`design/ux-blueprint.md`](../design/ux-blueprint.md) §4

## Goal

Users create Tracks ("Software Developer", "AI Engineer", "Product Manager", "Registered Nurse – Dubai") with precise criteria, edited in plain language or structured controls. Works for any occupation worldwide.

## Acceptance scenarios

1. "New Track" → choose template "AI Engineer" or describe in words → criteria compiled into chips/sections; summary sentence shown; save.
2. Edit the description ("also hybrid in Singapore, exclude agencies") → diff of criteria changes shown → apply.
3. Edit a chip directly (remove "Angular") → summary sentence updates.
4. Non-tech Track: "ICU nurse, night shifts, UAE or Saudi, visa sponsorship" compiles correctly with occupation code and location/visa filters.
5. Duplicate a Track, archive one, reorder in the sidebar; each Track has its own settings page (criteria, sources placeholder, schedule placeholder, autonomy level, caps, resume placeholder).
6. Live preview shows "Preview available after first discovery" until Phase 5 provides data (then a real count).

## Tasks

### Taxonomy
- [x] Import **ESCO** (occupations, skills, multilingual labels, occupation↔skill relations) and **O*NET** (SOC occupations, alternate titles, technology skills) into global tables; crosswalk ESCO↔ISCO↔SOC where available; refresh script.
- [x] Title normalizer: free-text title → candidate occupations (embedding similarity over labels + alt titles, LLM tiebreak) with confidence.
- [x] Skill normalizer: raw skill → canonical skill (aliases: "JS" → JavaScript, "K8s" → Kubernetes; multilingual). Back-fill `profile_skills` from Phase 3.
- [x] Synonym/adjacent-title suggester (from taxonomy + later from observed postings).

### Criteria model
- [x] `CriteriaV1` Pydantic schema (all dimensions in PRD F3): titles[] (+ synonyms, + exclude titles), occupations[], skills {must, nice, exclude}, seniority[], employment_types[], work_modes[], remote_eligibility {anywhere, regions[], countries[], timezone_overlap_hours, base_tz}, locations[] {place, radius_km}, visa_sponsorship, relocation, salary {min, max, currency, period, hide_unspecified}, companies {include[], exclude[], sizes[], industries[], stages[], exclude_agencies}, posting_max_age_days, languages[], education, clearance, keywords {include_expr, exclude_expr}, min_match_score, caps {per_day, per_company}.
- [x] NL compiler: text → `CriteriaV1` (strict structured output) + human-readable diff vs current; never drops existing fields silently (merge semantics with explicit removals).
- [x] Summary generator: criteria → one sentence (deterministic template first, LLM polish optional).
- [x] Compiled filter: criteria → SQL predicates + scoring weights used by Phase 6 (versioned; `track_criteria.version` increments).
- [x] Track CRUD, duplicate, archive, reorder, templates (seed 40+ templates across industries).
- [x] Geocoding for locations (free: Nominatim with caching and their usage policy, or GeoNames dump), timezone resolution.
- [x] Currency normalization table (daily rates from a free source, e.g. ECB reference rates), period normalization (hour/day/month/year → monthly).

### Frontend
- [x] Tracks list + sidebar entries (color, icon, counts).
- [x] Criteria builder per blueprint §4: NL box with "Update", chips per section, "More filters" drawer, boolean keyword editor with validation, location picker with radius, country multi-select with region presets (APAC, EU, LATAM...), timezone overlap slider, salary with currency/period, company include/exclude with autocomplete, preview panel.
- [x] Track settings tabs (placeholders for sources/schedule wired in Phases 5/10).

## Edge cases & failure modes

- Contradictory criteria (on-site in Berlin + remote only) → validation warning with a fix suggestion.
- Over-narrow (0 results later) → suggest relaxations ranked by gain (Phase 6 uses this).
- Ambiguous titles ("Consultant", "Associate") → ask the user to pick an occupation.
- Multilingual input ("Desarrollador backend") → compile to canonical + keep original as a title synonym.
- NL compiler hallucinating fields (e.g., invents salary) → the compiler may only set fields mentioned in the text; a post-check compares against the text.
- Salary in a currency with no rate → keep the original, exclude from normalized filters, show a note.

## Testing

- NL compiler eval set (≥ 60 descriptions across occupations/countries/languages) with expected criteria; field accuracy ≥ 90%, zero invented fields.
- Unit: compiled SQL for each dimension; currency/period normalization; geocode cache.
- E2E: create, edit by text, edit by chips, duplicate.

## Docs to update

`docs/architecture/criteria-and-taxonomy.md` (new), route guides, PRD F3 if dimensions change.

## Exit criteria

- [x] Scenarios 1–5 pass; eval targets met; taxonomy refresh script documented.
- [x] Screenshots: 30 files under `docs/design/screenshots/phase-04/` (5 surfaces × 375/820/1440 × light/dark).
- [x] `pnpm run ci:quality` green; E2E `e2e/tracks.spec.ts` green.
- [x] Architecture doc `docs/architecture/criteria-and-taxonomy.md` + route guides under `docs/guides/routes/tracks/`.
