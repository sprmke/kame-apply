# Phase 20: Response tracking, interview prep, coach/agency workspaces

**Status:** Done (eng) · **Release:** Later · **Depends on:** 17 · **Features:** F14 (responses), F17, team tenancy UI

## 20a. Response tracking

Forwarded/pasted recruiter replies → deterministic classify (rejection, interview, assessment, info request, offer) → **propose** status changes with citation; user confirms on `/responses`. Scam heuristics set `scam_level=red` and skip proposals.

- [x] Tables `response_messages`, `status_proposals` + RLS
- [x] Classifier + ingest + decide APIs
- [x] `/responses` UI
- [x] Cross-tenant tests

## 20b. Interview prep (F17)

Per application: company brief from known posting/application facts, likely questions, STAR stories from profile evidence, checklist. Truthfulness: no invented company claims.

- [x] `interview_preps` + generate/get APIs
- [x] Application detail UI section

## 20c. Coach / agency workspaces

Multi-profile selector UI with counts; active profile persisted per workspace.

- [x] `GET /coach/profiles`
- [x] `/coach` page + `useActiveProfile.selectProfile`

## 20d. Gap plan (F7 P2)

Track must-skills missing from profile → learning suggestions; status to completion.

- [x] `gap_plan_items` + refresh/list/patch
- [x] `/tracks/:id/gaps`

## 20e. Referrals

CSV contact import, company match on applications, outreach drafts (user sends).

- [x] `contacts`, `referral_drafts`
- [x] `/contacts` + application referral section

## Docs / quality

- [x] `docs/architecture/phase20-later.md`
- [x] Route guides for responses, coach, contacts, gaps; application detail notes
- [x] `pnpm run ci:quality` green

## Out of scope (later)

Gmail/Outlook OAuth sync, LinkedIn connections export automation, per-candidate invite ACLs, billing hooks.
