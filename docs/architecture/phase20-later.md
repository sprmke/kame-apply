# Phase 20: Responses, interview prep, gaps, referrals, coach

## Tables (migration `0033`)

| Table | Purpose |
| --- | --- |
| `response_messages` | Pasted/forwarded recruiter replies + classification + scam flags |
| `status_proposals` | Proposed application status changes; user accepts/dismisses |
| `interview_preps` | Per-application brief, questions, STAR stories, checklist |
| `gap_plan_items` | Track must-skill gaps with learning suggestions |
| `contacts` | User-imported CSV contacts |
| `referral_drafts` | Outreach text the user sends (never auto-sent) |

All rows are workspace-scoped with RLS.

## API

| Method | Path | Notes |
| --- | --- | --- |
| `POST` | `/api/v1/responses/ingest` | Classify reply; optional `application_id` → proposal |
| `GET` | `/api/v1/responses` | List messages |
| `GET` | `/api/v1/responses/proposals` | Pending (or filtered) proposals |
| `POST` | `/api/v1/responses/proposals/{id}/decide` | Accept or dismiss |
| `POST` | `/api/v1/responses/proposals/batch` | Batch decide |
| `GET/POST` | `/api/v1/applications/{id}/interview-prep` | Read / generate |
| `GET/POST` | `/api/v1/tracks/{id}/gap-plan` (+ `/refresh`) | List / suggest |
| `PATCH` | `/api/v1/gap-plan/{id}` | Status |
| `POST` | `/api/v1/contacts/import` | CSV-shaped JSON |
| `GET` | `/api/v1/contacts` | List |
| `GET` | `/api/v1/applications/{id}/referral-matches` | Company match |
| `GET/POST` | `/api/v1/applications/{id}/referral-drafts` | List / create draft |
| `GET` | `/api/v1/coach/profiles` | Multi-profile counts |

Classifier is deterministic (keyword patterns). Scam heuristics set `scam_level=red` and skip status proposals. Interview prep and referral drafts use only profile + application facts (P1).

## UI

| Route | Role |
| --- | --- |
| `/responses` | Paste replies; accept/dismiss proposals |
| `/coach` | Candidate profiles in the workspace |
| `/contacts` | Import and list contacts |
| `/tracks/:id/gaps` | Gap plan |
| `/applications/:id` | Interview prep + referral matches |
