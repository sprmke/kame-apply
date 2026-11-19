# Multi-industry support: industry packs

**Status:** In progress (IND-1 to IND-10 shipped) · **Created:** 2026-11-12 · **Type:** cross-cutting product + platform program (API, web, extension copy, AI, discovery)

Related: [`docs/prd.md`](../../prd.md), [`docs/architecture/industries.md`](../../architecture/industries.md), [`docs/architecture/criteria-and-taxonomy.md`](../../architecture/criteria-and-taxonomy.md), [`docs/architecture/job-discovery.md`](../../architecture/job-discovery.md), [`docs/architecture/matching.md`](../../architecture/matching.md), [`docs/architecture/profile.md`](../../architecture/profile.md), and [`ux-clarity-overhaul.md`](ux-clarity-overhaul.md) (onboarding `/start`, Searches tabs, glossary).

---

## 1. Goal

Kame Apply should work just as well for a chef, a nurse, an electrician, or a teacher as it does for a software engineer. Today it is shaped around tech: its sources, filters, scoring, profile fields, answers, and advice all assume tech work.

- **End goal:** any industry works on day one through a **General** pack plus AI. Curated packs add depth for the most common fields.
- **First priority:** two curated packs that are fully done end to end:
  1. **Technology** (software engineering and related). This mostly encodes what the app already does.
  2. **Hospitality and food** (chefs, cooks, kitchen and pastry roles first; front of house later).
- **UX promise:** the user picks what kind of work they do once, or we infer it from their resume. After that, every page shows only the controls, sections, words, and advice that fit that work. Nothing is locked away: every hidden control is still one tap away under **More options**.

### Success criteria

| # | Criterion | How we check |
| --- | --- | --- |
| M1 | A chef with only a resume and one sentence ("Sous chef in Dubai, accommodation provided") reaches 10+ relevant, real postings within the first run, for at least 3 target countries we commit to in IND-0 | Scripted run (§13.3) against live sources in staging; fixture version in CI |
| M2 | A chef never sees a tech-only control (GitHub, timezone overlap, tech stack, funding stage, coding practice) unless they open More options | Visibility matrix tests (§13.1) + `ux-clarity-review` on every pack-aware route |
| M3 | A software engineer's experience does not regress: same filters, same ranking quality, same sources | Existing ranking eval NDCG@20 holds; snapshot test on the Technology manifest |
| M4 | Adding a new curated industry needs **no component or router code**: only a pack file, i18n strings, templates, fixtures, and evals | The IND-10 packs ship as content-only PRs; enforced by the `industry-pack` skill checklist |
| M5 | Any field not covered by a curated pack gets a usable setup (titles, credentials, sources, filters) from General + an AI-drafted pack the user accepts | Eval over 50 "other" role descriptions (§12) |
| M6 | P1 to P7, RLS, the activity log, and a11y do not regress | `ci:quality`, `security-auditor`, cross-tenant tests, a11y smoke |

### Non-goals

- No separate app, theme, or navigation per industry. All industries get the same five primary nav items. Only the content changes.
- No industry-specific evasion, scraping of logged-in boards, or republishing (P2, P5 still apply).
- No multilingual UI in this program. Industry content is i18n-ready, English only for now.
- No employer-side features.

---

## 2. Audit: where the app assumes tech today

Checked against the current working tree on `main`.

| # | Where | Assumption | Effect on a chef |
| --- | --- | --- | --- |
| G1 | `apps/api/app/sources/discover.py` `_boards_for_run` | Every run polls the same 8 curated company boards, whatever the Track is | Chef searches poll tech company ATS boards and get almost nothing |
| G2 | `packages/py-core/kame_core/sources/adapters/*` | Layer 1 is Greenhouse/Lever/Ashby/Workable/SmartRecruiters/Recruitee; Layer 2 is Remotive/RemoteOK/Himalayas/Jobicy/Muse/Arbeitnow | Startup and remote-tech sources. Hospitality employers mostly use Workday, iCIMS, SuccessFactors, Taleo, Harri, Paradox, Fountain, or post only on Indeed/JobStreet/SEEK |
| G3 | `apps/api/app/sources/catalog.py` `COUNTRY_COVERAGE` | Coverage only for REMOTE/US/DE/EU/PH, all with tech boards | We can't tell a chef that coverage in their country is thin |
| G4 | Discovery has no query layer | Sources are polled by company, not searched by keyword + location | There is no way to ask for "cook jobs near Makati" |
| G5 | `tracks/criteria.py` | Seniority is `intern..executive`. No shifts, no "casual" or "seasonal" work, and the salary period defaults to `month` | Kitchen ranks (commis, chef de partie, sous, head) and shift work don't fit |
| G6 | `tracks/plan.py` prompt | Regions and remote-first framing, "core skills" language | Plans come out remote-heavy and tech-shaped |
| G7 | `matching/rule_score.py` | `DEFAULT_WEIGHTS` puts skills at 0.28 and location at 0.10. The generic-words list covers office titles only | For on-site hourly roles, location, shift, and credentials matter more than skills |
| G8 | `matching/extract.py` `_LICENSE` | Recognizes `license`, `certification`, `rn`, `cpa`, `pe` only | Misses food handler cards, ServSafe, HACCP, Food Safety Level 2, TESDA Cookery NC II, STCW, and RSA |
| G9 | `profiles/answer_keys.py` | `github_url` and `portfolio_url` are canonical for everyone. No availability, shift, transport, or food-safety keys | Wrong questions for hourly and hospitality forms |
| G10 | `gaps/suggest.py` | "Practice {skill} with a small portfolio project" | Bad advice for a cook |
| G11 | `strategy/linkedin.py` | GitHub checklist, LinkedIn-first "Be Found" | Hospitality hiring runs more through Indeed, JobStreet, SEEK, Culinary Agents, Harri, and Instagram |
| G12 | `profiles/schemas.py` `DocumentKind` and upload limits | PDF/DOCX/TXT/MD/JSON only | A chef can't upload photos of their dishes |
| G13 | `taxonomy/seed.py` | 24 occupations, about 18 of them tech or office. Of 40+ templates, only one is food-related ("Chef" occupation) and none are kitchen templates | Template picker and normalizer barely know kitchen titles |
| G14 | `ai/prompts.py` (`job_fit`, `resume_*`, `cover_letter`) | "Skeptical recruiter" framing. Tech metrics are implied | Weak critique for kitchen resumes (stations, covers, food cost, inspections) |
| G15 | `matching/embed.py` | English-only `bge-small-en-v1.5` | Fine for now. Becomes a risk once we add non-English markets (§14) |

None of these are bugs on their own. Together they make the app tech-only.

---

## 3. What other products do (references)

| Product | What they do | Lesson for us |
| --- | --- | --- |
| **LinkedIn** Open to Work | Keeps preferences small: titles, locations, workplace type, employment type. Adds fields per region (India adds notice period and expected salary, shown to recruiters only). Groups jobs by sector in "Job Collections". | Keep the core small and the same for everyone. Let **context add fields** (region, industry) instead of forking the form. Keep preferences private by default. |
| **SEEK / JobStreet** | A two-level taxonomy: a *classification* (Hospitality & Tourism) with *sub-classifications* (Chefs/Cooks). Users pick a classification first. | Use a two-level picker (field → role family) that users recognize, mapped under the hood to ISCO/ESCO, which we already store. |
| **Indeed** | Screener questions cover licenses, relocation, and clearance. Smart Screening checks licenses and certifications, and seekers can verify licenses during apply (pilots in GB/AU/CA, 2026). | In regulated and hourly work, **credentials are first-class** and often knockouts. Model them as structured facts with expiry, not free-text skills. |
| **Culinary Agents** | A hospitality-only network. The profile can be the resume. AI resume parser. "Willing to relocate" sits in job preferences. Posts are distributed to 500+ partner boards. | For hospitality, a complete profile matters more than a polished PDF. Relocation and accommodation are headline preferences. |
| **Harri** | Hospitality hiring platform. Shows seekers a profile score and response rate. Employers invite seekers to apply. | Track profile completeness **per pack**. Readiness means different things for a cook and an engineer. |
| **Instawork** | Certifications unlock shift types (Food Handler card, alcohol service). Uploads must show name, number, and issue/expiry dates. | Credential objects with expiry, plus a "this unlocks N more jobs" nudge. Never store more than needed (P4/PII). |
| **Chef resume guides** (hcareers, Escoffier, Novoresume) | Name stations run, covers per service, kitchen type, cuisine, and certifications (ServSafe, Food Safety Manager). Mention inspection records. One page. | The pack defines evidence types and resume rules: covers, food cost %, inspection results, and stations, not latency or ARR. |
| **Teal / Huntr / Jobscan** | Generic ATS-safe templates. Reviewers point out that generic templates miss sector content (clinical metrics, licenses, GitHub). | Resume templates and critique rubrics must be pack-aware. |
| **Adzuna / Jooble / Careerjet / USAJobs** | Keyword + location search APIs with categories (Adzuna has country-specific category tags such as IT and Hospitality). They cover all industries. | Add a **query layer** (Layer 4). It is the fastest compliant way to cover non-tech work in many countries. Terms must be verified per source (§7.2). |

Best-practice principles drawn from these:

1. **Same skeleton, different content.** One IA, one design system. Industry changes defaults, labels, visible fields, vocabulary, sources, and advice. It never changes the structure.
2. **Ask once, infer, confirm.** One tap at workspace creation, or none at all: infer from the resume and confirm with a chip.
3. **Progressive disclosure, never removal.** Hide what doesn't fit and keep it under More options. Data is never deleted when the industry changes.
4. **Config, not branches.** No `if industry === 'chef'` in components or routers. Everything reads a resolved manifest.
5. **Occupation, not employer sector.** A chef at a hospital is still a chef. Packs key off *what you do* (ISCO/ESCO occupation). The employer's sector stays a filter (`companies.industries`).
6. **A useful General fallback.** Unknown fields still work through taxonomy + AI. Curated packs add depth; they aren't required.

Sources: [LinkedIn job preferences help](https://www.linkedin.com/help/linkedin/answer/11783), [LinkedIn Job Collections and Preferences](https://www.socialmediatoday.com/news/linkedin-adds-new-tools-for-job-seekers-including-job-preference-highlight/704791/), [SEEK Chefs/Cooks listings](https://au.seek.com/Chef-jobs/contract-temp), [Indeed Smart Screening](https://www.indeed.com/employers/smart-screening?hl=en), [Indeed Smart Screening release notes](https://www.indeed.com/employers/cs/smart-screening/release-notes), [Indeed screener questions](https://docs.indeed.com/indeed-apply/screener-questions), [Culinary Agents](https://culinaryagents.com/), [Culinary Agents resume help](https://culinaryagents.com/resources/how-to-submit-your-resume), [Harri alternatives review](https://oysterlink.com/spotlight/harri-alternatives), [Instawork certifications](https://help.instawork.com/en/articles/12985330-adding-professional-certifications), [Instawork food handler requirement](https://help.instawork.com/en/articles/2845577-getting-your-certifications-for-instawork-hospitality-gigs), [hcareers chef resume](https://www.hcareers.com/article/job-search-tips/how-to-create-a-chef-resume), [Escoffier chef resume tips](https://www.escoffier.edu/blog/culinary-pastry-careers/8-tips-for-writing-a-chef-resume/), [Line cook resume guide](https://resumegeni.com/resume-guides/line-cook-resume-guide), [Industry-specific resume gaps](https://resources.rework.com/tools/ai-tools/best-ai-resume-builders-2026), [Adzuna developer overview](https://developer.adzuna.com/overview), [Jooble API](https://jooble.org/api/about), [Careerjet API overview (vendor blog)](https://jobspipe.dev/blog/careerjet-api), [USAJobs API overview (vendor blog)](https://jobspipe.dev/blog/usajobs-api), [Free job APIs list (Arbeitnow)](https://www.arbeitnow.com/blog/job-board-api), [Workday career-site JSON (dev.to)](https://dev.to/udaninn/workday-job-boards-have-a-json-api-too-its-just-better-hidden-23fl).

Some of these sources are vendor blogs. Every source's terms, quotas, and attribution rules get checked against the official terms in IND-0 before an adapter is built.

---

## 4. Core concept: the industry pack

An **industry pack** is a declarative, versioned, code-reviewed description of how the app behaves for one field of work. Every layer reads it: discovery, matching, profile, answers, resume, AI prompts, safety, and UI visibility. Components and services never branch on the industry key. They read the pack.

### 4.1 Where the industry lives (decision)

| Level | Field | Meaning |
| --- | --- | --- |
| **Workspace** | `workspace_industries` rows: one `is_primary`, zero or more extra | The fields this workspace works in. Chosen at creation or onboarding. Drives defaults and global pages (Profile, Answers, Today, Studio). |
| **Track (Search)** | `tracks.industry` (required, defaults to the workspace primary) | Each search belongs to one pack. Drives that search's criteria UI, sources, scoring, tailoring, and safety. |
| **Profile** | No industry column | Profile sections shown = union of the workspace's enabled packs. One person can be a cook *and* a developer. |
| **Job (global)** | `jobs.industry_hints`, `jobs.occupation_code` | Classified at ingest, so board selection, coverage, and matching can use them. |

**Why both levels:** the user asked for a workspace-level choice, and that covers the common case (the chef friend gets a Hospitality workspace). Track-level membership covers the real edge cases: someone searching two fields, a coach (`/coach`, "People I help") running searches for several people, or a career changer. Global pages use the union so nothing the person needs is hidden.

### 4.2 Pack schema (`apps/api/app/industries/schema.py`)

```text
class IndustryPack(BaseModel):            # frozen, extra="forbid"
    key: str                              # "technology", "hospitality", "general", ...
    version: int                          # bump on behavior change; stored on tracks for traceability
    label_key: str                        # i18n key, e.g. "industry.hospitality.label"
    icon: str                             # Phosphor, e.g. "ph:cooking-pot"
    detection: Detection                  # ISCO groups, ESCO prefixes, title keywords, resume cues
    role_families: list[RoleFamily]       # 2nd level of the picker (Kitchen, Pastry & bakery, Front of house...)
    ui: UiManifest                        # visible / collapsed / hidden fields, section order, label overrides
    facets: list[FacetDef]                # industry-specific dimensions (cuisine, station, kitchen type...)
    criteria_defaults: CriteriaPatch      # work modes, salary period, posting age, employment types
    seniority_ladder: list[LadderStep]    # local rank names mapped onto CriteriaV1 Seniority
    credentials: list[CredentialDef]      # names, aliases, regions, typical validity, knockout weight
    answer_keys: AnswerKeyPlan            # add / hide canonical answer keys
    sources: SourcePlan                   # preferred adapters, Adzuna categories per country, query templates,
                                          # employer directory tags, email-alert recommendations per country
    matching: MatchingPlan                # weights, generic title words, title equivalence groups, knockout rules
    profile: ProfilePlan                  # section order/labels, evidence metric patterns, interview gap questions
    resume: ResumePlan                    # template id, section order, bullet guidance, photo norm per country
    ai: AiBrief                           # short brief (<= 600 chars) + vocabulary injected into prompts
    safety: SafetyPlan                    # extra scam signals (placement fees, pay-for-training, visa fees)
    features: FeatureFlags                # be_found, github_links, coding_practice, portfolio_images, ...
```

Supporting types (all `extra="forbid"`):

- `FacetDef(key, kind: multi|single|bool|range, options: list[FacetOption(key, label_key, synonyms)], applies_to: {criteria, profile, job}, match: {filter, boost, ledger_only}, group: str)`. Synonyms drive rule-based extraction from postings and resumes.
- `CredentialDef(key, label_key, aliases, countries, validity_months, knockout: bool)`, e.g. `food_handler`, `servsafe_manager`, `haccp`, `food_safety_l2_uk`, `tesda_cookery_nc2_ph`, `stcw_basic` (cruise), `rsa_au`.
- `LadderStep(key, label_key, maps_to: Seniority, aliases)`, e.g. kitchen hand/commis → junior, chef de partie → mid, sous chef → senior, head chef → lead, executive chef → manager/director.
- `UiManifest(criteria: {group: [field ids]}, collapsed: [ids], hidden: [ids], profile_sections: [ids], labels: {field_id: i18n_key}, nav: {feature: visible})`.

### 4.3 Registry and resolution

- Curated packs live in code: `apps/api/app/industries/packs/{general,technology,hospitality}.py`. They are versioned and reviewed, with schema tests.
- `GET /api/v1/industries` lists packs (key, label, icon, role families) for the picker. Global, read-only.
- `GET /api/v1/workspaces/{id}/experience` returns the **resolved experience manifest**: enabled packs, the primary pack, the merged UI manifest for global pages, and per-pack manifests for tracks. The web app caches it in Vue Query and invalidates it when industries change.
- Resolver rules (`industries/resolve.py`, pure functions, unit-tested):
  - Global pages: the **union** of visible fields across enabled packs. A field is hidden only if *every* enabled pack hides it.
  - Track pages: that Track's pack only.
  - `general` is always the base layer. Packs override it, never the other way round.
  - Custom (AI-drafted) packs can only *choose among* existing facet kinds, credentials, and fields. They can't add new field types or weaken safety rules.
- **Hiding is UX only.** The API still accepts every CriteriaV1 field for every pack. A hidden field with a saved value is shown with a "set earlier" marker so it never acts invisibly.

### 4.4 Data model changes

| Change | Table / file | Notes |
| --- | --- | --- |
| New tenant table `workspace_industries` | `(workspace_id, industry_key, is_primary, custom_pack jsonb null, created_at, updated_at)` | RLS + forced policy, partial unique index on primary, cross-tenant test. `custom_pack` holds an accepted AI-drafted pack for "Something else". |
| `tracks.industry varchar(48) not null default 'general'`, `tracks.industry_version int` | `tracks` | Backfill: template `industry` → pack, else the classifier over titles/occupations, else `technology` for pre-existing rows (all current data is tech). Record the backfill in `deployment.md`. |
| `CriteriaV1.shifts: list[Shift]` | `tracks/criteria.py` | New core field, not a facet, because hospitality, healthcare, retail, logistics, and security all use it. `Shift = morning|afternoon|evening|night|weekend|split|rotating`. Additive optional field; `schema_version` stays 1. |
| `CriteriaV1.facets: dict[str, list[str] | bool | int]` | `tracks/criteria.py` | Keys validated against the Track's pack in the service (unknown keys → 422 with field path). |
| `EmploymentType` adds `casual`, `seasonal` | `tracks/criteria.py` + rule extract | Common in AU/NZ/UK hospitality and cruise. |
| `SalaryFilter.includes: list[accommodation|meals|tips|service_charge|transport]` | `tracks/criteria.py` | Live-in and overseas kitchen roles often pay partly in kind. |
| Global `jobs.industry_hints text[]`, `jobs.occupation_code`, `jobs.facets jsonb` | `jobs` (no RLS) | Filled at ingest by the rule classifier, later by optional LLM. GIN index on `industry_hints`. |
| Global `companies.industries text[]`, `company_boards.industries text[]` | discovery tables | Lets runs pick boards by Track industry + country. |
| Global `source_coverage(source_key, country, industry, coverage, note)` | replaces `COUNTRY_COVERAGE` constant | Seeded from packs. Powers the coverage notice (§8.6). |
| New tenant table `profile_facets` | `(id, workspace_id, profile_id, facet_key, value, source, do_not_use, confidential, sort_order)` | RLS. Evidence refs become `facet:<id>` so tailoring can cite "Filipino and Japanese cuisine" truthfully (P1). |
| `profile_certifications` adds `credential_key`, `expires_on` | profiles | Links a cert to a pack credential for knockouts and expiry nudges. The new migration from `0039` already widened `kind`. |
| Answer keys gain `packs: tuple[str, ...]` | `profiles/answer_keys.py` | Catalog filtered per workspace. New keys in §9.3. |
| Documents allow `image/jpeg`, `image/png`, `image/webp`, `image/heic` for `kind=portfolio` | `profiles/documents.py` | EXIF/GPS stripped on finalize (location privacy), size caps, ClamAV stub, R2 only (invariant 6). |

All migrations are new Alembic files (never edit shipped ones). Every mutation writes an `activity_log` event (§11).

---

## 5. Curated packs: first two, then the roadmap

### 5.1 Technology (encode today's behavior)

Its contents come from current defaults, so a tech user sees no change: remote eligibility + timezone overlap visible, skills ("Tech stack") primary, funding stage and company size visible, GitHub/portfolio answer keys, Be Found with the GitHub checklist, current weights, current sources (Layer 1 ATS + remote boards), and current templates. The snapshot test pins its manifest.

### 5.2 Hospitality and food (first new pack)

**Role families (picker level 2):** Kitchen (cook, line cook, prep cook, commis, chef de partie, sous chef, head chef, executive chef, kitchen hand); Pastry and bakery; Catering and banquets; Cruise and resort kitchens; Front of house (server, barista, bartender, host; in v1 these have titles only and get full depth later).

**Criteria UI (Search > What to look for):**

| Group | Fields | Default |
| --- | --- | --- |
| Role | titles + ladder (Kitchen hand to Executive chef) | from plan |
| Where | locations with **commute radius** prominent, relocation, countries (for overseas work), visa sponsorship | radius 15 km, on-site |
| When | **shifts**, employment type incl. casual/seasonal | any |
| Pay | salary with **hourly** period default, `includes` (accommodation, meals, tips, service charge) | hour or month per country |
| Kitchen (facets) | cuisine, kitchen type (fine dining, casual dining, hotel, banquet/catering, QSR, cruise, institutional, bakery, central kitchen), station (grill, sauté, garde manger, pastry, fry, prep, expo), volume (covers per service band) | any |
| More options (collapsed) | keywords, company include/exclude, company size, posting age, languages, match floor | |
| Hidden for this pack | timezone overlap, base timezone, funding stage, clearance, "tech stack" label (skills relabeled "Skills and techniques") | |

**Credentials:** food handler card (US county/state), ServSafe Food Handler/Manager, HACCP, UK Food Hygiene Level 2/3, AU RSA (front of house), TESDA Cookery NC II (PH), culinary diploma, STCW basic safety (cruise), seaman's book (cruise, stored as "have it: yes/no" only, never the number). Credentials marked `knockout` feed the knockout predictor.

**Answer keys:** add `food_safety_certificate` (have + expiry), `availability_days`, `shift_preference`, `weekend_holiday_availability`, `earliest_start_date`, `hourly_rate_expectation`, `reliable_transport`, `accommodation_needed`, `knife_kit` (own kit yes/no), `trial_shift_ok`. Hide `github_url`. Physical-requirement questions ("Can you stand for 8 hours / lift 20 kg?") are **never auto-answered**. They raise `unknown_required` so the user answers each time, because health and disability are sensitive classes (P4, `pii-guard.mdc`).

**Profile:** section order is Experience (labeled "Kitchen experience" when this pack is primary) → Certifications (moved up) → Skills and techniques → Cuisines and stations (facets) → Signature dishes and menus (stored in the existing `profile_projects` table, label only) → Education → Languages. Photo portfolio upload. Evidence metrics: covers per service, food cost %, waste reduction %, inspection scores, team size, menu items created, rating/award.

**Matching:** weights favor location 0.18, title 0.22, credentials (new component) 0.12, shift 0.08, skills 0.15, seniority 0.10, salary 0.08, freshness 0.07. Title equivalence groups (cook ≈ line cook ≈ commis cook; CDP ≈ chef de partie ≈ station chef). Generic words add `cook`, `chef`, and `crew` when they appear alongside a more specific token, so "Pastry chef" doesn't match "Sous chef" at 35.

**Sources:** see §7. In short: Adzuna `hospitality-catering-jobs`-style category per country, Jooble/Careerjet keyword search (if terms allow), hotel/cruise/restaurant-group career sites through JSON-LD, Workday and SuccessFactors adapters (if terms allow), and guided email alerts for Indeed/JobStreet/SEEK/Culinary Agents/hcareers.

**Resume:** one-page template, certifications near the top, "Kitchen skills" block, no GitHub/links section unless provided, photo **off by default**. Optional photo per country norm (PH, Gulf, parts of EU), which the user turns on (`minimization.photo`).

**Interview prep:** trial shift / stage checklist (knife kit, uniform, arrival, tasting, mise en place questions), common kitchen interview questions, menu tasting prep.

**Safety:** extra signals: placement or processing fees, pay-for-uniform/training/medical, "visa fee" requests, cruise and Gulf recruitment-agency fees. For PH workers going abroad, a reminder to check the agency's license with the Department of Migrant Workers. The DMW license lookup's exact availability gets verified in IND-0, and we link out to it, never scrape it.

**AI brief (example):** "Hospitality and food roles. Evidence that matters: stations run, cuisines, covers per service, kitchen type, food safety credentials with expiry, food cost and waste numbers, inspection results, team size. Ranks: kitchen hand, commis, chef de partie, sous chef, head chef, executive chef. Do not invent cuisines, covers, or certifications."

### 5.3 General (fallback, always present)

All core fields visible with neutral labels. Taxonomy-driven titles. Generic credentials detection (`license|licence|certified|registration`). Balanced weights. Sources: query layer + JSON-LD + alerts. Used for any industry without a curated pack, and as the base layer under every pack.

### 5.4 Roadmap packs (IND-10, content-only PRs, in this order)

1. **Healthcare** (nurse, caregiver, allied health): license + state/country registration, specialty, unit, shift, agency vs direct.
2. **Engineering, non-software** (mechanical, civil, electrical, chemical): PE/CEng/registration, sector (construction, energy, manufacturing), site vs office, CAD tools.
3. **Skilled trades** (electrician, plumber, welder, mechanic): license/ticket, own tools, own vehicle, travel radius, apprenticeship level.
4. **Customer service and retail**: shifts, languages, BPO vs in-house (strong PH market), typing speed answer key.
5. **Education**: license/registration, subject, grade level, school calendar.
6. **Logistics and driving**: license class, endorsements, routes, vehicle.
7. **Finance and accounting**: CPA/ACCA, software, close cycle.
8. **Admin and virtual assistant**: remote, tools, time zones (shares fields with Technology).
9. **Sales and marketing**, **Creative and design**: mostly UI/labels over General.

Each pack: role families, facets, credentials, answer keys, sources plan, templates (≥10), fixtures, evals (§12), i18n.

---

## 6. UX and UI

Signal design system only (cool canvas, white surfaces, indigo brand, Manrope, Phosphor, Reka UI). Copy follows `human-copy` and `minimal-ui-copy` (and the policy update proposed in UX-0 of the UX overhaul). Every new surface gets empty, loading, error, and permission-limited states, checked at 375/820/1440 in light and dark.

### 6.1 Choosing the industry

**A. Create workspace (`CreateWorkspaceDialog.vue` becomes a 2-step dialog)**

```text
Step 1  Name                 [ Ana's job search          ]
Step 2  What kind of work?   [ Search fields...          ]
        ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
        │ ph:code    │ │ ph:cooking │ │ ph:first-  │ │ ph:wrench  │
        │ Tech and   │ │ Hospitality│ │ aid        │ │ Trades     │
        │ software   │ │ and food   │ │ Healthcare │ │            │
        └────────────┘ └────────────┘ └────────────┘ └────────────┘
        ... (curated packs first, then "Something else")
        + Add another field          Not sure? We'll work it out from your resume.
                                           [Back]  [Create]
```

- Single-select by default, with **Add another field** for a second one. The first pick is primary.
- **Skip is allowed.** It sets `general` and lets onboarding infer the field.
- "Something else" opens a one-line describe box ("I fix boat engines") → AI suggests the closest curated pack or drafts a custom pack (§10.3) as a pencil draft the user accepts.

**B. Onboarding `/start` (UX overhaul §8.2) gets a confirm step after resume parse**

```text
Looks like kitchen work.   [Hospitality and food ✓]  [Change]
Role family: Kitchen · Level: Sous chef
```

The classifier (§10.1) uses parsed titles, ISCO codes from the taxonomy normalizer, and credentials. If the workspace already has a field, we only confirm. If the resume clearly disagrees ("you picked Tech, your resume is all kitchens"), we offer to switch or add, never silently.

**C. Settings > General > Fields of work** (new section in `settings/general.vue`)

- List of fields with a primary star, Add, Remove (removing a field used by active searches asks first, offers to move those searches to General, and never deletes data).
- Changing the primary field shows a **preview of what changes** ("Profile will show Certifications higher. GitHub link moves to More options. New searches default to on-site and hourly pay.") before saving.

**D. New search (Searches > New search sheet)**

- The field chip at the top defaults to primary. The template tab shows that pack's templates first, with tabs for other enabled packs.
- "Describe it" infers the pack from the text. If it differs from primary, a chip says "Hospitality and food" with **Change**.

### 6.2 What changes per field (visibility matrix)

`●` shown, `◐` under More options, `○` hidden (still reachable through More options > Show all), `✎` relabeled.

| Surface / control | General | Technology | Hospitality | Notes |
| --- | --- | --- | --- | --- |
| Criteria: titles + ladder | ● | ● | ● ✎ kitchen ranks | Ladder labels from pack |
| Criteria: skills | ● | ● ✎ Tech stack | ● ✎ Skills and techniques | |
| Criteria: remote eligibility, timezone overlap | ● | ● | ○ | |
| Criteria: commute radius | ◐ | ◐ | ● | |
| Criteria: shifts | ◐ | ○ | ● | |
| Criteria: salary period default | month | month/year | hour (or month by country) | |
| Criteria: salary includes (accommodation, meals, tips) | ◐ | ○ | ● | |
| Criteria: facets (cuisine, kitchen type, station, volume) | n/a | n/a | ● group "Kitchen" | |
| Criteria: funding stage, company size | ◐ | ● | ○ | |
| Criteria: clearance, education | ◐ | ◐ | ○ | |
| Profile: Projects | ● | ● | ✎ Signature dishes and menus | Same table |
| Profile: Certifications position | normal | normal | moved up, expiry shown | |
| Profile: Portfolio images | ◐ | ○ | ● | |
| Answers: `github_url` | ◐ | ● | ○ | |
| Answers: availability/shift/transport/food safety | ◐ | ○ | ● | |
| Jobs fit panel ("How you match") | core rows | + stack, timezone | + credentials, shift, commute, accommodation | Ledger rows from pack |
| Search > Improve > LinkedIn tips (Be Found) | ● | ● + GitHub | ✎ "Get found": Indeed/JobStreet/Culinary Agents profile tips + Instagram portfolio | `features.be_found` |
| Skill gaps advice | generic | portfolio project | short course/cert, stage, trial shift | `gaps/suggest.py` reads pack |
| Interview practice | generic | technical rounds | trial shift / stage | |
| Studio template | default | default | one-page chef | |
| Safety extra signals | base | base | + placement/pay-for-training/visa-fee | |
| Auto-submit "Always manual" list | LinkedIn/Indeed/JobStreet | same | same | P3 unchanged |

Implementation: one composable `useExperience()` in `apps/web/app/composables/useExperience.ts` returns `visible(id)`, `collapsed(id)`, `label(id, fallback)`, `facets(trackId)`, `pack(trackId)`. A tiny `<FnIf feature="criteria.shifts">` wrapper is optional. Components never read the pack key directly. A lint rule (`check:industry-branches` script) flags `industry ===` / `pack.key ===` in `apps/web/**` and routers.

### 6.3 Making hidden things discoverable

- Every criteria group ends with **More options**. At the bottom of the page, **Show all filters** reveals every field and remembers the choice per Track (localStorage, convenience only).
- If a hidden field has a saved value, it is shown inline with a "Set earlier" tag and a clear button.
- The command bar searches all fields regardless of visibility ("timezone" finds the field and opens More options).

### 6.4 Thin coverage, honestly

When `source_coverage` for (industry, country) is `thin` or the first run returns fewer than 5 jobs:

```text
Few chef jobs from our sources in Cebu yet.
Add a job alert from JobStreet and we'll read it for you.   [Set up in 2 minutes]
Other options: search nearby cities · include Metro Manila · add a company's careers page
```

This links into Settings > Alerts with pack-specific, country-specific guides (§7.4) and the relaxation suggestions that already exist (`matching/relax.py`).

### 6.5 Route guides to add or update

`docs/guides/routes/settings/general.md` (Fields of work), `tracks/settings.md` + `tracks/detail.md` (pack-aware criteria), `profile/index.md` (sections), `profile/answers.md`, `jobs.md` (ledger rows), `settings/alerts.md` (pack guides), `studio.md`, `coach.md`, new `onboarding` guide from the UX overhaul.

---

## 7. Discovery: finding non-tech jobs on the internet

This is the biggest functional gap (G1 to G4). Without it, a chef gets no jobs no matter how good the UI is.

### 7.1 Track-aware source selection (fix G1)

`_boards_for_run(session, track)` selects boards by `company_boards.industries && pack.sources.employer_tags` and by country/region from the Track's locations, weighted by `poll_tier`. A per-run board limit stays. Layer 2/4 sources come from `pack.sources.adapters`. `track_sources` toggles still win.

### 7.2 New Layer 4: query search APIs

New adapter kind `search` in `kame_core/sources`: `fetch(query=SearchQuery(keywords, location, country, radius_km, category, posted_within_days, page))`. Each adapter gets a terms note, descriptive UA, rate limit, block-signal fail-closed behavior, recorded fixtures, and health metrics (`source-adapter` skill).

| Adapter | Why | To verify in IND-0 |
| --- | --- | --- |
| `search_adzuna` | Many countries, category tags per country (incl. hospitality), salary data | Free-tier quota, attribution/link-back rules, caching window, supported countries |
| `search_jooble` | 60+ countries, keyword + location | Key approval for our use case, quota, display rules |
| `search_careerjet` | 90+ countries | Publisher terms, tracking-redirect links (keep the link, P5) |
| `search_usajobs` | Free official API, includes federal food service | User-Agent contact rules (use a generic project contact, never the user's email) |
| `search_reed` (UK), `search_jobbank_ca` (Canada open data) | Strong national coverage | Terms and data licence |
| EURES (EU), DMW/PhilJobNet (PH), Workforce Australia | Official national sources | Whether a public API or feed exists; otherwise skip |

Rules:

- **Platform keys, not user keys,** for search APIs (env vars, `docs/architecture/configuration.md`). A missing key disables that adapter cleanly (P7: still free to run, with lower coverage).
- **Shared query cache:** global `source_query_cache(source_key, query_hash, fetched_at, result_refs)` so 50 workspaces searching "cook Manila" cost one call per window. Results go into the global `jobs` pool through the existing upsert + dedupe path.
- **Query planner:** the search plan (§10.2) emits `source_queries` per adapter (keywords, category tag, location strings) from titles + pack mappings. The plan is stored on the Track and shown in Search > Where we look as plain rows ("Adzuna: 'sous chef' in Dubai, Hospitality").
- Apply URL preference stays ATS > career page > board.

### 7.3 Employer career sites for non-tech employers

- Keep `career_jsonld` (schema.org JobPosting) as the default path. Hotels, cruise lines, and restaurant groups often publish JobPosting markup for Google for Jobs.
- Evaluate `ats_workday` and `ats_successfactors` adapters. Those endpoints are the career site's own JSON, not a documented public API, so IND-0 checks terms and robots, and we decide per vendor. If in doubt, use JSON-LD only.
- Seed an **employer directory per pack and country** (`company_boards.industries`): international hotel groups, cruise lines, airline catering, contract caterers, and large restaurant groups in the committed countries. Status `candidate` until validated (existing directory flow).
- Users can still add a careers URL (`POST /sources/careers`). The pack's "Where to look" card suggests it.

### 7.4 Email alerts as a first-class path for hospitality

Indeed, JobStreet/SEEK, and LinkedIn alert parsers already exist (Phase 17). Add:

- Parsers for Culinary Agents, hcareers, Harri, and Poached alerts (generic parser first, specific ones from saved fixtures).
- **Guided alert setup per pack and country** in Settings > Alerts: "Create a JobStreet alert for *Commis chef* in *Makati*, then forward it to your Kame address," with the pre-filled search terms from the Track's titles and a copy button. No automation of the board itself (P2, P5).
- The onboarding finish step suggests this when coverage is thin.

### 7.5 Classify jobs at ingest

`jobs/classify.py` (rule-first): title → taxonomy normalizer → ISCO → pack, plus description cues (facets, credentials). Writes `industry_hints`, `occupation_code`, `facets`. An optional bulk-tier LLM tiebreak runs only for low-confidence jobs and only when budget allows. This makes coverage stats and matching per pack possible.

### 7.6 Clipper and extension

The extension clipper works on any page already. Add pack-aware field extraction hints (credentials, shifts) to `extension/brain.py`. The job still saves through the API (UI-only extension, invariant 1).

---

## 8. Matching and scoring

| Change | Module | Detail |
| --- | --- | --- |
| Pack weights as defaults | `rule_score.py` `DEFAULT_WEIGHTS` → `pack.matching.weights`, still learned per Track and still bounded | Tech keeps today's numbers |
| Credentials component | new `matching/credentials.py` | Required credential in posting vs profile cert (by `credential_key` or alias). Expired → warn, not block (P4). |
| Shift component | `rule_score.py` | Criteria shifts ∩ job facets.shifts. Unknown → neutral |
| Commute | `rule_score.py` location | Uses existing geocode + radius. On-site packs weight distance |
| Title equivalence + generic words per pack | `rule_score.py`, `hard_filters.py` | Pack groups count as equal titles. Ladder aliases map to seniority |
| Facets | `hard_filters.py` (filter facets), `rule_score.py` (boost facets) | `match` mode per `FacetDef` |
| Qualification extract | `extract.py` | `_LICENSE` and new patterns come from all packs' credentials + facets. Shift/schedule, physical-requirement, and accommodation/meals cues |
| Knockouts | `knockout.py` | Credential knockouts. Physical requirements → `unknown_required` checkpoint, never auto-answered |
| Fit ledger rows | `verdicts.py` + Jobs drawer | Rows labeled from the pack ("Food safety certificate", "Weekend shifts", "12 km away", "Accommodation provided") |
| LLM `job_fit` | prompt v2 | Pack brief + facet vocabulary in the system prompt. Posting stays delimited untrusted data |

---

## 9. Profile, answers, resume, and advice

### 9.1 Profile

- `profile_facets` CRUD under `/api/v1/profiles/{id}/facets` (same patterns as other sections: `do_not_use`, `confidential`, `source`).
- `profile_extract` prompt v2 gets the brief and facet vocabulary of the workspace's enabled packs, so stations and cuisines are pulled into facets, and certifications get `credential_key` + `expires_on`.
- Interview (`profiles/interview.py`): gap questions from `pack.profile.gap_questions` ("How many covers on a busy night?", "Which stations have you run?", "Any food cost or waste numbers?").
- `evidence_strength`: metric patterns from the pack (covers, %, food cost, inspection score), not only digits.
- Completeness meter per pack (like Harri's profile score): for Hospitality, credentials with expiry, stations, cuisines, one metric bullet per role, availability.

### 9.2 Portfolio images

Image upload for `kind=portfolio`, a gallery in Profile > Documents, optional link in resume/answers ("Portfolio link" generates a private, expiring share URL only on explicit user action; default off). EXIF/GPS stripped.

### 9.3 Answer bank

- `CanonicalKey.packs`. `GET /answers/keys` filters by the workspace's enabled packs (plus the existing `custom` group).
- Quick setup (`answers/setup`) seeds pack keys and drafts values from profile facts where safe (UX overhaul A3).
- Apply engine and extension autofill read the same catalog, so hospitality forms (Harri, Paradox-style questions) map to the new keys.

### 9.4 Resume Studio, tailoring, cover letters

- `ResumePlan`: template id, section order, bullet guidance, and the photo norm per country (off by default, user-enabled).
- Prompts `resume_critique`, `resume_lens`, `resume_tailor_review`, `cover_letter` v2 take the pack brief and a rubric. Lens persona from the pack ("head chef hiring for a busy brigade"). Truthfulness and evidence refs unchanged (P1). Facets cite `facet:<id>`.
- Fabrication evals per pack (§12).

### 9.5 Advice features

- `gaps/suggest.py`: suggestions from `pack.profile.gap_actions` (cert course, stage, short course) instead of "portfolio project".
- `strategy/linkedin.py` → "Get found": per-pack checklist. Technology keeps LinkedIn + GitHub. Hospitality covers LinkedIn basics, Indeed/JobStreet/SEEK profile, Culinary Agents/Harri profile, and Instagram portfolio hygiene. Route `tracks/[id]/be-found.vue` reads the checklist from the API.
- Interview practice (`interview`): pack question bank + trial-shift checklist.
- Salary advice (`strategy/salary.py`): period and `includes` from the pack. Never invents figures (only sourced posting data).

---

## 10. AI: what it does, with guardrails

Every AI step is tool-less with delimited untrusted input (P6), budget-aware with a deterministic fallback (P7), produces a draft the user accepts (invariant 3), logs on accept, and has an eval.

### 10.1 Industry detection (`industry_detect.v1`)

- Input: parsed titles, skills, certs, or a role description. Output: `{pack_key, role_family, confidence, reasons[]}`.
- Deterministic first: taxonomy normalizer → ISCO → `pack.detection`. The LLM runs only when rules are below a confidence threshold. Fallback is `general`.
- Used in workspace creation ("Something else"), onboarding confirm, new-search inference, ingest tiebreak (bulk tier, budget-capped), and the backfill.

### 10.2 Pack-aware search plan (`search_plan.v2`)

- Adds the pack brief, ladder, facet options, credentials, and the country to the prompt. Outputs titles in the **local market's words** (e.g. "Commis 1", "Cook (Filipino cuisine)", "Kitchen helper"), facets, shifts, a salary period hint (never an amount), and `source_queries`.
- Still never proposes salary amounts, visa, cities, companies, education, or clearance (current guard). The invent guard extends to facets: options must exist in the pack.
- Deterministic baseline per pack (nearest template + pack defaults), so no-AI mode still works.

### 10.3 Custom pack drafting for "Something else" (`industry_pack_draft.v1`)

- From a description ("marine diesel mechanic, cruise ships"), the model *selects* from existing building blocks: closest base pack, role family names, which core fields to show or hide, credentials from a global credential catalog (or free-text names marked unverified), search terms, and email-alert suggestions.
- Stored in `workspace_industries.custom_pack` after the user accepts. It can't change safety rules, P-rules, or field types. A schema validator rejects anything else.
- Over time, frequent custom packs (by anonymized pack-key counts only, never content) tell us which curated pack to build next.

### 10.4 "Where to look" advisor (`source_advice.v1`)

- Given pack + country, the model proposes **candidate** niche boards and employer career pages as a draft list. Each entry goes through the existing career-page detector, robots check, and terms note before it can be enabled, and the user confirms. The model never fetches pages, and nothing it says is executed.
- **Optional web discovery provider** (decision D5): a self-hosted SearXNG (P7) or a free-tier search API configured at the platform level, used only to find employer career URLs, which then go through the same detector. Off by default.

### 10.5 Job facet extraction

Rule extract first (pack synonyms). `qual_extract` v2 adds pack vocabulary for low-confidence postings, bulk tier, cached by `qualifications_hash` as today.

---

## 11. Security, privacy, tenancy, audit

| Topic | Rule |
| --- | --- |
| RLS | `workspace_industries`, `profile_facets` are tenant tables with forced RLS + cross-tenant tests. `jobs.*`, `source_coverage`, `source_query_cache`, and directory columns are global, no tenant data |
| Never trust the client | The server resolves the manifest. `tracks.industry` must be one of the workspace's enabled packs (422 otherwise) |
| PII | Health/physical questions → `unknown_required`, never stored as answers. Seaman's book / ID numbers are never stored (only yes/no). Photos off by default. EXIF stripped. Credential numbers not required |
| Untrusted input | Role descriptions, resumes, postings, and alert emails stay delimited data |
| Source access | Every new adapter: terms note, UA with a generic project contact, rate limits, robots, fail closed. Platform contact details only, never user details (global rule) |
| Activity log | `workspace.industry_added`, `workspace.industry_removed`, `workspace.industry_primary_changed`, `workspace.custom_pack_accepted`, `track.industry_changed`, `profile.facets.created|updated|deleted`, `document.portfolio_image_added`. Store keys and counts only, never descriptions or facet text if confidential |
| RBAC | Changing workspace industries: owner/admin. Track industry: anyone with `data.write` |
| `security-auditor` | Required for IND-1 (tables), IND-4 (adapters), IND-6 (images), IND-9 (AI web discovery) |

---

## 12. Evals and fixtures

| Eval | Set | Gate |
| --- | --- | --- |
| Industry detection | ≥300 titles + 60 resume snippets across 10 fields (incl. ambiguous: "pastry chef at a hospital", "IT support in a hotel") | top-1 ≥90%, curated pack recall ≥95% for tech + hospitality |
| Search plan per pack | ≥60 hospitality descriptions added to `tests/evals/fixtures/criteria/` | role signal present, no invented salary/visa/location/facets, title accuracy ≥85% |
| Qual extract hospitality | ≥50 postings (cook, sous chef, cruise, hotel banquet, bakery) | credential recall ≥95%, shift extraction ≥85% |
| Ranking | ≥200 hospitality pairs | NDCG@20 ≥ rule-only baseline. Tech eval unchanged (M3) |
| Tailoring fabrication | 15 chef profiles × 3 postings | zero invented cuisines/certs/covers. Every claim has an evidence ref |
| Custom pack draft | 50 "other" descriptions | schema-valid 100%, no safety field changes, usable titles ≥85% (human-graded once, then recorded) |
| Safety | scam fixtures: cruise placement fee, Gulf visa fee, pay-for-training | flagged at ≥medium risk |

Source fixtures: recorded responses per new adapter under `apps/api/tests/fixtures/sources/<adapter>/`. CI never calls live APIs.

---

## 13. Testing and verification

### 13.1 Automated

- Pack registry tests: every pack validates, every i18n key exists in `en.json`, every referenced adapter/answer key/credential/template exists, no pack weakens a P-rule field.
- Resolver unit tests: union rules, primary override, hidden-with-value behavior.
- Visibility matrix test: generate the §6.2 table from the manifests and diff it against a committed snapshot.
- API: industries list, experience manifest, workspace industries CRUD (RBAC + audit), track industry validation, facets validation, `profile_facets` CRUD, image upload + EXIF strip.
- Cross-tenant tests for both new tenant tables.
- Vitest: `useExperience`, the criteria form rendering per pack, the create-workspace stepper, and "Show all filters".
- `check:industry-branches` script in `ci:quality` (no `industry ===` in web components or routers).

### 13.2 E2E (Playwright)

1. Tech user regression: an existing workspace looks the same (screenshot diff at 1440).
2. Chef journey (below), fixture sources.
3. Two-field workspace: Tech + Hospitality searches side by side. Profile shows the union. Each search shows only its own filters.

### 13.3 Scripted chef run (manual, staging, live sources)

1. Create workspace "Ana" → pick Hospitality and food.
2. Upload a real (consented) chef resume → confirm "Kitchen work, Sous chef".
3. Profile shows Kitchen experience, Certifications with expiry, Cuisines and stations. No GitHub anywhere.
4. New search: "Sous chef in Dubai, accommodation provided, full time" → chips: Sous chef / Chef de partie / Senior CDP, on-site, includes accommodation, posting ≤21 days.
5. Run → ≥10 relevant postings (M1). Coverage notice if thin.
6. Open a job → the ledger shows food safety cert, shift, and accommodation rows.
7. Tailor → one-page chef resume, no invented cuisines. The cover letter reads like a kitchen, not a startup.
8. Safety → a fixture posting with a "processing fee" is flagged.

Repeat for the other committed countries (D2).

---

## 14. Risks

| # | Risk | Mitigation |
| --- | --- | --- |
| R1 | Search API terms forbid our use, or free quotas are too low | IND-0 verification before any build. Shared query cache. Email alerts + JSON-LD as fallback paths |
| R2 | Config sprawl makes packs hard to reason about | One schema, registry tests, snapshot of the visibility matrix, `industry-pack` skill checklist |
| R3 | Hiding a filter hides a saved constraint | "Set earlier" tag on hidden fields with values. Server ignores nothing |
| R4 | Wrong auto-detected industry | Always a confirm chip. Easy change. Never silent switches |
| R5 | Scope creep into many packs | Ship Tech + Hospitality fully first. Others are content-only PRs after |
| R6 | English-only embeddings for non-English markets | Out of scope now. Note for a later multilingual embedder (`bge-m3` class) when a non-English country is committed |
| R7 | Overlap with the UX overhaul and uncommitted work on `main` | Land or stash current work first. IND-2 builds on UX-3/UX-4 components where they exist, or ships the minimal version and UX slices restyle it |
| R8 | Health/physical questions in kitchen forms | Always a human checkpoint (`unknown_required`). Tests prove no auto-answer |

---

## 15. Delivery plan (slices)

Each slice is one branch and PR (`ind/NN-<slug>`), follows the repo build loop (`/ka-start-work` scratchpad, test first where practical, docs in the same change, `/ka-check-before-pr`). The **Friend MVP** milestone is marked ★ and gets the chef friend real value as early as possible.

| Slice | Scope | Exit criteria |
| --- | --- | --- |
| **IND-0 Decisions and verification** ★ | Answer §16. Verify terms/quotas for Adzuna, Jooble, Careerjet, USAJobs, Reed, Job Bank, EURES, Workday/SuccessFactors endpoints, the DMW lookup. Commit target countries. Write the `industry-pack` skill + `.cursor/rules/industry-packs.mdc` + `/ka-new-industry-pack` command (run `python3 .codex/sync.py`, `check:ai-tooling-sync`) | Decisions recorded in this file. Terms notes drafted per adapter. Tooling synced |
| **IND-1 Pack foundation** ★ ✅ | `industries/` package (schema, registry, resolver), General + Technology packs (today's behavior), `workspace_industries`, `tracks.industry` + backfill, `CriteriaV1.shifts/facets/includes` + `casual/seasonal`, `GET /industries`, `GET /workspaces/{id}/experience`, regenerated API client | No behavior change for tech (M3 snapshot). RLS + cross-tenant tests. Backfill documented in `deployment.md` |
| **IND-2 Picker and visibility** ★ ✅ | Create-workspace step 2, Settings > Fields of work with change preview, new-search field chip, `useExperience`, pack-driven criteria groups, More options + Show all, "Set earlier" tags, `check:industry-branches` | Visibility matrix snapshot passes. 375/820/1440 light/dark. `design-reviewer` pass |
| **IND-3 Hospitality pack content** ★ ✅ | Role families, ladder, facets, credentials, answer keys, defaults, ≥15 templates, AI brief, i18n, profile section plan | Registry tests green. Template picker shows kitchen templates |
| **IND-4 Discovery for non-tech** ★ ✅ | Track-aware board selection, Layer 4 adapters (`search_jooble`, `search_adzuna`, terms-gated), shared query cache, query planner, `jobs/classify.py`, `source_coverage`, coverage notice, `Where we look`, guided alert links + Culinary Agents guide | Fixture E2E returns and links hospitality jobs; `/sources/coverage`, `/tracks/{id}/where`, `/sources/alerts/guide` tested |
| **IND-5 Matching** ★ ✅ | Pack weights, credentials + shift components, title groups, facets in filters/boost, commute distance, credential extract, ledger rows | Hospitality matching unit tests; existing tech matching tests unchanged |
| **IND-6 Profile and answers** ✅ | `profile_facets` CRUD + RLS, profile UI section, pack-filtered answer keys, hospitality answer keys, image portfolio with EXIF strip, credential key on certifications | Facet CRUD + RLS tests, answer-key filtering test, EXIF test |
| **IND-7 Resume, tailor, letters** ✅ | Pack-aware resume sections/order, certifications/projects/languages, `profile_extract` v2, resume/critique/cover-letter prompt v2 with field brief, template id recorded | Chef sections render in pack order; prompt brief test |
| **IND-8 Advice, safety, interview** ✅ | Gaps per pack, "Get found" checklist, interview questions + trial shift, placement/visa/uniform fee signals, salary period/includes | Safety fixture flags, pack checklist and interview tests |
| **IND-9 AI assists** ✅ | Deterministic `industry_detect`, `search_plan.v2` baseline, custom pack drafting + accept, source advice; AI prompt entries for each | Detection, search plan, custom pack, advice endpoint tests |
| **IND-10 More packs** ✅ | Healthcare, Engineering, Trades, Customer service/retail, Education, Logistics, Finance, Admin/VA, Sales/Marketing, Creative as content packs | Registry/i18n tests; no component or router diff |

Suggested order: IND-0 → IND-1 → (IND-3 ∥ IND-4) → IND-2 → IND-5 = Friend MVP. Then IND-6 → IND-7 → IND-8 → IND-9 → IND-10.

Docs per slice: `docs/architecture/industries.md` (new, the canonical pack reference), `criteria-and-taxonomy.md`, `job-discovery.md`, `matching.md`, `profile.md`, `configuration.md` (search API keys), `deployment.md` (migrations, backfill), `overview.md` §3 if checkpoint use changes, `docs/prd.md` (multi-industry scope, Track definition examples beyond tech), route guides (§6.5), `docs/design/glossary.md`, `docs/phases/` (new phase file or a phase-21 entry, decided in IND-0), and this file's status.

---

## 16. Open decisions (need your answer before IND-1)

| # | Decision | Recommendation |
| --- | --- | --- |
| D1 | Industry at workspace only, or workspace default + per-search | **Workspace default + per-search** (§4.1). Same simple UX for one field, handles two-field people and coaches. **Answered 2026-11-12: workspace default + per search.** |
| D2 | Which countries does the chef friend target (home country, Gulf, cruise, AU/CA/UK)? | Commit 2 to 3 countries for M1. Source choice depends on this more than anything else. **Answered 2026-11-12: Philippines + UAE/Gulf first.** |
| D3 | Front of house in v1 or later | **Later.** Kitchen first, front of house titles only in v1 |
| D4 | Platform-level search API keys (we hold them) vs BYO per workspace | **Platform-level** with a shared cache. BYO only if quotas force it |
| D5 | Optional web discovery (SearXNG / search API) for finding employer career pages | **Yes, off by default,** URLs only, through the existing detector + user confirm |
| D6 | Workday/SuccessFactors JSON endpoints | Decide per vendor after the terms check. Default to JSON-LD only |
| D7 | Phase numbering: new `phase-21-multi-industry.md` vs a standalone program like the UX overhaul | **New phase file**, with these slices as its checklist |
| D8 | Sequencing against the UX overhaul | Run UX-0/UX-1 first if they're already started. Otherwise start IND-0/IND-1, which have no UI conflict |

---

## 17. Production review (2026-11-14)

A second pass ran in an isolated worktree (`ind/production-review`) against the committed program
branch. Full `pnpm run ci:quality` passed: 595 API tests, 14 runner tests, 21 UI, 18 web, 9
extension, and 103 eval-lite tests (1 live skip).

Security audit fixes:

- Provider failures no longer persist or serve URLs/query strings with Adzuna/Jooble keys. A new
  migration also scrubs existing `sources.last_error` rows.
- `workspace_industries` and `profile_facets` revoke the read-only role, matching other tenant
  tables.
- Custom packs are re-derived server-side from `description` and `base_pack`; the brief is
  sanitized and fenced as data. A client cannot post arbitrary prompt or safety content.
- Facet writes are limited to enabled pack options and reject sensitive numbers.
- Resume verification and parse confirmation include `profile_facets`; parsed facets come from
  the confirmed draft, not raw document text.
- Image dimensions are checked before decode, the cap is 20 MP, and re-encoding runs off the event
  loop.
- Manual "Run now" has a per-workspace daily cap; scheduled runs keep each schedule's cap.
- Custom-pack updates and default track sources both emit audit rows.
- Stored custom packs that no longer validate fall back to General instead of breaking the
  workspace.

Design review fixes:

- Workspace picker tiles use the 2px brand focus outline and `edge` borders.
- The custom field input has a real label, a short placeholder, and a stacked button.
- Custom packs show a Draft chip and pencil text until accepted; the short label is backed by the
  full name in the accessible label and tooltip.
- Drafting prepends the tile, preserves existing selections, and announces when the limit is hit.
- The "Set earlier" summary no longer reports an implicit timezone default for hidden fields.

Provider terms were reviewed on 2026-11-13 from the official help pages:

- Jooble: regional REST API, 100 requests/day per regional key; a key only works on the domain that
  issued it. The adapter now uses `{country}.jooble.org` and reads `JOOBLE_API_KEY_PH` and
  `JOOBLE_API_KEY_AE`.
- Adzuna: 25 requests/minute, 250/day, 2,500/month free tier; attribution required and commercial
  product use needs a licence after a 14-day evaluation. Adzuna has no PH or AE market, so those
  searches skip it instead of sending a doomed request.

Live calls are gated on the operator setting `SEARCH_TERMS_ACKNOWLEDGED=true` and keys. With the
operator keys in place, live staging calls succeeded on 2026-11-13:

- Jooble PH, Manila, `sous chef`: 5 of 5 sample jobs returned.
- Jooble AE, Dubai, `sous chef`: 5 of 5 sample jobs returned.
- Adzuna GB, London, `sous chef`: 5 of 5 sample jobs returned.

A local Kame search then ingested 30 Jooble jobs for Dubai and 28 for Manila and scored them. The
run exposed two discovery defects, both fixed with tests:

- A stale track could keep older tech ATS source rows, and the board loop also allowed any board
  when `career_jsonld` was enabled. Hospitality tracks could poll Greenhouse tech boards. Discovery
  now intersects enabled sources with the pack allowlist and only polls a board whose adapter is
  allowed.
- `linked` stayed at 0 even when new TrackJobs were created because the counter was lost during the
  background progress commit. The completed run now reconciles `linked` from the TrackJob count
  delta.

A local Ollama `qwen2.5:7b` call through the app's tool-less structured path returned
`hospitality` at 0.9 confidence for a Dubai sous chef description. That exposed a provider
compatibility issue: `job_fit` used native tool output, which the local model could not satisfy.
It now uses `PromptedOutput`, like the resume prompts and `profile_extract`.

The hospitality employer seed was checked: Accor, Compass Group, Hilton, Marriott, Carnival, Royal
Caribbean, and Sodexo return HTTP 200 but expose no JSON-LD job postings on the landing page; Hyatt,
IHG, and Radisson return 403 and stay candidate/unpolled. Carnival, Royal Caribbean, and Sodexo URLs
were corrected in the seed. None were promoted to active because the JSON-LD adapter found no
JobPosting records.
