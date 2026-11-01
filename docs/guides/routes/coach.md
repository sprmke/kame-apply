# Route: `/coach`

**Page:** `apps/web/app/pages/coach.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Profile list | — | — | Documented | Phase 20c |
| Add profile | — | name required | Documented | cap 10 |

## Overview

Coach/agency view of candidate profiles in the workspace. Selecting a profile sets the active profile for Career Profile and related screens.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/coach/profiles` | Profiles + application counts |
| `POST /api/v1/profiles` | Create candidate profile |

## RBAC

`data.read` / `data.write` as for profiles.
