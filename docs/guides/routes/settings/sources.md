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
| Add | `POST /api/v1/sources/careers` | Detect ATS + slug; insert `company_boards` |
| (read) | `GET /api/v1/sources/health` | Catalog metrics |
| (read) | `GET /api/v1/sources/directory/stats` | Active board count |

## RBAC

Owners/admins only for health list. Add careers: `data.write`.
