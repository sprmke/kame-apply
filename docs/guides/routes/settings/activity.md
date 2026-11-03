# Route: `/settings/activity`

**Page:** `apps/web/app/pages/settings/activity.vue` · **Layout:** `default` · **Access:** owner or admin

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Event list | pytest `test_activity_limits_rewrap.py` | n/a | Done | Filter and Load more |

## Overview

The workspace's audit trail.

## User-facing knowledge

Shows what changed and when: renames, member changes, invitations, AI key changes. It never shows secrets.

**Common user questions**

- **Can events be edited or deleted?** No. The log is append-only.

## List

Newest first with a filter; times in your timezone. Load more uses a `(created_at, id)` cursor, so events written in the same transaction (identical timestamps) are never skipped.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/activity` | Filters: action (prefix ends with a dot), target type, actor, `before` + `before_id`, limit. Response carries `next_before` / `next_before_id`. |

## Implementation map

`pages/settings/activity.vue`; i18n `activity.*`.
