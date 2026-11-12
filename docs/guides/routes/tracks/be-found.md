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


## Field-aware checklist

The checklist below Open to work comes from the Track's industry pack (`pack.profile.found_checklist`), not a fixed GitHub list. Technology keeps the GitHub steps; Hospitality shows Indeed, JobStreet, SEEK, Culinary Agents, food safety expiry, and portfolio-photo steps. The API field is still `github_checklist` for compatibility.
