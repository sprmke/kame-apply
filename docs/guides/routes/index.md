# Route: `/ (Today)`

**Page:** `apps/web/app/pages/index.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Guided next step | acceptance.spec.ts | n/a | Done | Resume, search, run, or review matches |
| New matches | — | — | Documented | Top three with score, reason, risk |
| Your searches | — | — | Documented | Match and shortlist counts |
| Needs-you | — | — | Documented | Only when a decision is waiting |
| This week | — | — | Documented | Collapsed numbers, not a dashboard |
| Onboarding checklist | acceptance.spec.ts | n/a | Done | When home empty |
| Verify banner | acceptance.spec.ts | n/a | Done | |

## Overview

Guided daily brief: one next step (add resume, start a search, run the first search, or review matches), then the top three new matches, the user's searches, and Needs-you. Numbers and activity live under **This week**. Empty workspaces show the setup checklist.

## User-facing knowledge

The primary button always names the next action. Open a search to see its matches, or use **View all** to open the full Jobs list.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/home` | Brief payload (needs-you, KPIs, tracks, reminders, activity) |
| `GET /api/v1/ai/credentials` | Onboarding AI key step (owners and admins) |

## RBAC

`data.read` for home.

## Implementation map

`pages/index.vue`, `components/OnboardingChecklist.vue`, `components/VerifyEmailBanner.vue` · `apps/api/app/applications/home.py`

## UX clarity (2026-11-12)

- One next step card, then **Needs you** (deduplicated, link to `/needs-you`), then **Top matches**, then your searches.
- Top matches show the score as a small tabular badge, the company and work mode, one reason, and a risk seal only when it matters.
- Every number links to its filtered list. **This week** is a collapsed summary with full labels, not trailing fragments.
- First search after setup lands on the search's Matches tab rather than an empty Today.
