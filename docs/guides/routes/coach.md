# Route: `/coach`

**Page:** `apps/web/app/pages/coach.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Profile list | — | — | Documented | Phase 20c |
| Add profile | — | name required | Documented | cap 10 |
| Start from their resume | setup-from-resume.spec.ts | file type and size by the API | Documented | Creates a non-default profile and opens `/start?setup=` |

## Overview

Coach/agency view of candidate profiles in the workspace. A short lede explains that opening a profile shows that candidate's applications. Selecting a profile sets the active profile for Career Profile and related screens.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/coach/profiles` | Profiles + application counts |
| `POST /api/v1/profiles` | Create candidate profile |

## RBAC

`data.read` / `data.write` as for profiles.

## UX clarity (2026-11-12)

- The nav item and page title both say **People I help**.
- The page explains the feature in one line and offers **Add person** in a normal section.
- **Start from their resume** creates a profile named "New person", uploads the file, and opens the setup draft. Applying it renames the profile from the resume header.
