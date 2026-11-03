# Phase 18: Be Found + smart application strategy

**Status:** Done (eng) · **Release:** R2 · **Depends on:** 14 · **Features:** F19, F20 · **Reference:** [`research/07`](../research/07-how-recruiters-find-and-screen.md) §2(A,E), §3 · [`architecture/strategy.md`](../architecture/strategy.md)

## Goal

Increase inbound recruiter contact and application quality: an optimized, consistent LinkedIn presence (user-pasted), and strategy features that raise interview odds (freshness, caps, follow-ups, salary).

## Acceptance scenarios

1. Per Track: suggested LinkedIn headline (≤ 220 chars), About section, top skills order, experience title/description wording, all truthful, with copy buttons and a "why" for each.
2. Paste current LinkedIn profile text → consistency report vs Career Profile/resume (dates, titles, companies, skills) with fixes.
3. "Open to work (recruiters only)" checklist with target titles/locations from the Track.
4. Per-company cap (default 3 active applications per company per 90 days) warns before exceeding in runner preflight (`policy.warnings`), never blocks; freshness boost visible ("Posted 6h ago").
5. Salary suggestion for an application: posting range + market data → suggested truthful answer within the user's floor.
6. Follow-up drafts at day 7/14 (user sends).

## Tasks

- [x] LinkedIn optimizer prompts + verifier; consistency checker; checklist content.
- [x] Cap enforcement in Phases 13/15 preflight; warning UX.
- [x] Salary advisor using posting salary + Adzuna histograms + user floor.
- [x] Follow-up drafter + reminders (extends Phase 11).
- [x] GitHub/portfolio checklist for technical Tracks (README quality, pinned repos), as suggestions only.

## Exit criteria

- [x] Scenarios 1–6 covered by unit + API tests (truthful skills filter, headline length, caps, salary floor, follow-ups, freshness, cross-tenant); docs updated; `pnpm run ci:quality` green.
