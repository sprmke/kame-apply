# Route: `/ (Today)`

**Page:** `apps/web/app/pages/index.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Brief header | acceptance.spec.ts | n/a | Done | Greeting + optional headline from `/home` |
| Needs-you | — | — | Documented | Phase 10/11 |
| KPI tiles | — | period | Documented | Phase 11 |
| Track cards | — | — | Documented | pipeline mini-bar |
| Reminders / runs / activity | — | — | Documented | Phase 10/11 |
| Onboarding checklist | acceptance.spec.ts | n/a | Done | When home empty |
| Verify banner | acceptance.spec.ts | n/a | Done | |

## Overview

Daily command center: needs-you strip, period KPIs, Track pipeline cards, follow-up reminders, upcoming runs, recent activity. Empty workspaces still show the setup checklist.

## User-facing knowledge

Pick Today / This week / All time for the numbers. Open a reminder to jump to that application.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/home` | Brief payload (needs-you, KPIs, tracks, reminders, activity) |
| `GET /api/v1/ai/credentials` | Onboarding AI key step (owners and admins) |

## RBAC

`data.read` for home.

## Implementation map

`pages/index.vue`, `components/OnboardingChecklist.vue`, `components/VerifyEmailBanner.vue` · `apps/api/app/applications/home.py`
