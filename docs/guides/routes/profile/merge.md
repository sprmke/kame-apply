# Route: `/profile/merge/:documentId`

**Page:** `apps/web/app/pages/profile/merge/[documentId].vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Conflict list + additions | Partial | API | Documented | Opens when confirm returns `merge_required` |

## Overview

Resolve conflicts and choose additions when confirming a second resume against an existing profile.

## User-facing knowledge

When a new resume overlaps jobs you already confirmed, pick keep, replace, or skip for each conflict, then add any new items you want.

## Save paths

| UI | API | Effect |
| --- | --- | --- |
| Load | `GET /api/v1/profiles/{id}/documents/{doc}/merge` | conflict + addition preview |
| Resolve | `POST .../merge` | applies resolutions; confirms document |

## RBAC

Owner, admin, member can resolve. Viewer cannot.

## Agent parity

No MCP write for merge resolve yet (Phase 12b).

## Implementation map

`apps/web/app/pages/profile/merge/[documentId].vue`, `apps/api/app/profiles/merge.py`.
