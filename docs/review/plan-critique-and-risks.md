# Plan critique, risks, and failure modes

**Last updated:** 2026-10-28. A skeptical review of the whole plan: where it could fail to help users, and what the plan does about it. Re-run this review at the end of Phases 9, 14, and 16.

## 1. "Will this actually help someone land interviews?" (product-level critique)

| Weakness | Why it matters | Mitigation in plan |
| --- | --- | --- |
| Feature sprawl: 20 features, 21 phases | Solo builder never ships; half-finished features feel "crappy" | MVP cut (PRD §4a); R1 dogfood gate (Phase 14) before the runner; each phase has acceptance scenarios run in the real app |
| Matching quality is everything | Bad matches mean the user stops opening the app | Ranking evals (NDCG), dogfood check in Phase 6, feedback learning, explainable reasons so bad matches are diagnosable |
| Tailoring could make resumes *worse* (keyword-stuffed, generic) | Fails human skim and fraud checks | Truthfulness verifier, stuffing caps, reviewer pass, blind A/B eval (≥ 80% prefer tailored), skim view |
| Recruiter Lens might be a fake "ATS score" | Users over-trust a simulation | Labeled as simulation; requirement-level evidence instead of a single magic number; **outcome calibration**: track interview rate by Lens grade and recalibrate (Phase 11 outcome analytics) |
| Eligibility errors (remote "US only" shown to a PH user) | Wasted applications, frustration | Eligibility is `unclear` unless evidenced; knockout predictor; posting quote shown |
| Notification noise | User mutes the app | Strong-match threshold, digest default, instant only for Needs-you |
| Onboarding too long | Drop-off before first value | 5-minute path: upload → confirm → template Track → first matches + critique |
| Free LLM tiers are slow/limited | AI features feel broken | Budget-aware funnel (AI only on top N), bulk-tier models, graceful degradation badges, BYO key |
| Spray-and-pray users | Their outcomes worsen; looks spammy to employers | Per-day and per-company caps, quality coaching copy, research/07 evidence shown in the UI |

## 2. Platform, legal, and policy risks

### 2.1 LinkedIn specifically (important correction)

LinkedIn's User Agreement prohibits third-party software **including browser plugins and add-ons** that scrape or copy data from the service, and automated methods of access. Popular extensions do operate on LinkedIn, but risk exists even with a human present. Plan decisions (applied to Phase 13):

- **LinkedIn clip = minimal:** save URL + title + company the user is viewing; then resolve the same job on the employer's ATS (most LinkedIn postings originate there) and ingest from the ATS. No profile data, no bulk page copying, no background tabs.
- **LinkedIn Easy Apply autofill: off by default**, opt-in per workspace with an explicit acknowledgment of LinkedIn's terms (kame-hunt's owner accepted this risk for personal use on 2026-10-23). Even when enabled, it fills only on user click, one step at a time, and never clicks Next/Submit.
- Prefer applying on the company ATS whenever the job exists there.
- The same per-platform policy table covers Indeed and JobStreet/SEEK (terms reviewed at implementation; defaults conservative).

### 2.2 Other risks

| Risk | Mitigation |
| --- | --- |
| Unofficial endpoints (Workday cxs, LinkedIn guest) change or object | Health monitoring, circuit breakers, Layer-6 opt-in only; turn off on request |
| Board API terms (Adzuna attribution "Jobs by Adzuna", Careerjet link requirements, Remote OK/Remotive attribution, no republishing) | `terms_note` per adapter; attribution rendered in UI; jobs visible only inside the workspace |
| Dataset/taxonomy licenses (ESCO, O*NET attribution; EMSCAD terms for commercial use) | Attribution page; verify EMSCAD license before commercial use, otherwise train only on our own labeled data |
| Gmail restricted scopes (verification + paid assessment) | Forwarding-address design; Gmail API only for self-hosted/personal |
| Chrome Web Store rejection | Single purpose, minimal permissions, privacy policy, limited-use disclosure (Phase 13) |
| Privacy law (GDPR, PH Data Privacy Act 2012, CCPA): resumes are personal data | Consent at sign-up, privacy policy, export/delete, data minimization, processor list (LLM providers), breach procedure |
| **Free LLM tiers may use inputs for training** (some providers' free API tiers do) | Show per-provider data-use notes in AI settings; recommend paid/BYO or local Ollama for resume data; allow a "no free-tier for personal data" switch |
| EU AI Act / NYC LL144 | Candidate-side tool; transparent AI explanations; re-check before EU marketing (research/07 §4) |
| Abuse: someone uses the app to spam employers or test stolen identities | Caps, email verification, per-workspace limits, anomaly detection, ToS |

## 3. Technical risks

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| DBOS immaturity or a missing feature | Medium | Phase 1 spike; Hatchet fallback; workflows behind a thin internal interface |
| Oracle Free capacity/limits (halved June 2026; region shortages; reclaim of idle instances) | Medium-High | Hetzner €4–6 fallback with the same Compose; local runner; keep instance active |
| 12 GB RAM ceiling (Postgres + API + Chromium + fastembed + ClamAV) | Medium | Runner concurrency 2; ClamAV on demand; memory budgets per container; local runner offload |
| Postgres growth (jobs text) | Medium | Compression of closed jobs, retention, global dedupe, partitioning by month later |
| Cross-tenant leak | Low-Critical | RLS + app scoping + automated cross-tenant suite in CI from Phase 2 |
| SSRF via link resolver/career crawler/email links | Medium | Deny private IP ranges and metadata IPs, DNS-rebinding protection, egress allowlist for runner |
| Prompt injection via postings/emails/resumes | High | Sanitizer, data-only prompts, no tools on reading calls, eval corpus (Phase 7) |
| ATS form drift breaks adapters | High | Fixture tests, generic fallback, telemetry on unknown fields, form signature cache |
| LLM output variance breaks structured flows | Medium | Strict Pydantic outputs + retries + deterministic fallbacks; recorded-response tests |
| Claude Agent Bridge: injection reaching a user's Claude that has shell access; policy changes; plugin remote-OAuth unverified | Medium | Untrusted-data envelopes + sanitizer on all MCP outputs, plugin guard hooks, drafts-only writes, feature flag; see research/08 §4 and Phase 12b |
| Vue/Nuxt is new to the owner and has fewer ported agent skills than the React tooling | Medium | Write `nuxt-conventions`/`vue-components`/`vue-query-data` skills in Phase 0, vet community Nuxt skills, Phase 1 spikes (Hey API + Vue Query, WXT + shared UI), `context7` for current docs |
| A new design system takes longer than reusing old tokens and may drift | Medium | Phase 2 explores 2–3 variations on real screens, then locks `DESIGN.md`; `/_design` style guide + visual snapshots + `design-reviewer` agent every UI phase |
| AGPL contamination | Low | No AGPL code copied (ApplyPilot, Skyvern, OpenResume, PyMuPDF); dependency license check in CI |

## 4. Gaps found in this review and fixed in the plan

| Gap | Fix |
| --- | --- |
| LinkedIn extension policy too permissive | §2.1 → Phase 13 updated |
| UI internationalization missing ("every job on the planet" implies non-English users) | Phase 2: i18n framework + locale formatting from day one; English first |
| No feedback loop from real outcomes to Lens/ranking | Phase 11: outcome analytics (interview rate by method, Lens grade, tailored vs base, source) |
| Terminal input for checkpoints (asked in the brief) | Phase 15: local runner supports terminal prompts as an extra checkpoint channel |
| Why not Vercel/Supabase (asked in the brief) | tech-stack §5a |
| LLM free-tier data-use privacy | PRD F16 + AI settings note |

## 5. Effort sizing (rough, solo developer + agents)

| Phase | Size | | Phase | Size |
| --- | --- | --- | --- | --- |
| 0 Tooling | S | | 11 Tracker/home | M |
| 1 Scaffold + spikes | M | | 12 Answer Desk | S |
| 2 Auth/tenancy/shell | L | | 13 Extension | L |
| 3 Profile | L | | 14 Hardening/launch | M |
| 4 Tracks/criteria | M | | 15 Runner | XL |
| 5 Discovery | XL | | 16 Live view | L |
| 6 Matching/board | L | | 17 Email/push | M |
| 7 Safety | M | | 18 Be Found | S |
| 8 Resume Studio | L | | 19 Auto-submit | M |
| 9 Tailoring/Lens | L | | 20 Later | — |
| 10 Scheduling | M | | | |

S ≈ 1–3 sessions, M ≈ 4–8, L ≈ 8–15, XL ≈ 15+. R1 is roughly two-thirds of total effort; that's intentional, since R1 holds most of the value.
