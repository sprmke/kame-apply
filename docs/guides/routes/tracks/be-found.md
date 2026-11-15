# Route: `/tracks/:id/be-found`

**Page:** `apps/web/app/pages/tracks/[id]/be-found.vue` · **Access:** signed in

## Progress overview

| Section | Status |
| --- | --- |
| LinkedIn suggestions | Documented |
| Open to work / GitHub | Documented |
| Consistency paste | Documented |

## Overview

Per-Track Be Found: truthful LinkedIn copy with copy buttons and why text; paste current LinkedIn for a consistency report.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/tracks/{id}/linkedin-optimize` | Suggestions |
| `POST /api/v1/strategy/consistency` | Report |

## Implementation map

`apps/web/app/pages/tracks/[id]/be-found.vue` · `apps/api/app/strategy/` · `docs/architecture/strategy.md`

Location line reads the criteria the Track stores: `locations[].place` with its `country`, plus `work_modes` and `remote_eligibility` for remote. It no longer reads the unused `label` and `city` fields, so cities appear in the Open to work checklist.
