# Route: `/settings/sources`

**Page:** `apps/web/app/pages/settings/sources.vue` · **Access:** managers (`activity.read`)

## Overview

Per-adapter health (success, errors, latency, circuit, blocks) and the number of job boards checked. The lede frames the page as where searches look and whether each site is answering. Add a company career site link to grow the global board directory.

## Sections

- **Directory line.** "64 job boards checked."
- **Legend.** One sentence on what "Paused by us" means.
- **Add a company career site.** Labelled field plus Add. The site is detected and stored; success is a toast.
- **Health list.** One row per source: name, kind, state, jobs found, errors, response time, blocks.

## Save paths

| UI | API | Effect |
| --- | --- | --- |
| Add | `POST /api/v1/sources/careers` | Detect the ATS + slug and insert `company_boards`. A page that is not a known ATS is stored as a `career_jsonld` board so the JSON-LD reader can use it. |
| (read) | `GET /api/v1/sources/health` | Catalog metrics |
| (read) | `GET /api/v1/sources/directory/stats` | Active board count |

## Edge cases

- A known ATS URL (Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee) is read through that ATS API.
- Any other public careers URL becomes a `career_jsonld` board. The reader only picks up pages that publish `JobPosting` JSON-LD, so a marketing page adds a board with nothing to find.
- Search providers (Jooble, Adzuna) need platform keys in `apps/api/.env` and acknowledged terms. Without them a field that relies on search has no automatic source; the track page says so and offers job alerts.

## RBAC

Owners/admins only for health list. Add careers: `data.write`.
