# Route: `/legal/data-deletion`

**Page:** `apps/web/app/pages/legal/data-deletion.vue` · **Layout:** none · **Access:** public

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Deletion policy | a11y-smoke | n/a | Done | Phase 14 |

## Overview

How export and delete work for team workspaces, personal workspace limits, and backup retention.

## Implementation map

`pages/legal/data-deletion.vue`; API: `GET /api/v1/workspace/export`, `DELETE /api/v1/workspace`.
