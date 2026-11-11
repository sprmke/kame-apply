# Route: `/settings/sources`

**Page:** `apps/web/app/pages/settings/sources.vue` · **Access:** managers (`activity.read`)

## Overview

Per-adapter health (success, errors, latency, circuit, blocks) and directory board count. The page lede frames this as the health of the boards and career pages used by searches. Add a careers URL to grow the global board directory.

## Save paths

| UI | API | Effect |
| --- | --- | --- |
| Add | `POST /api/v1/sources/careers` | Detect ATS + slug; insert `company_boards` |
| (read) | `GET /api/v1/sources/health` | Catalog metrics |
| (read) | `GET /api/v1/sources/directory/stats` | Active board count |

## RBAC

Owners/admins only for health list. Add careers: `data.write`.
