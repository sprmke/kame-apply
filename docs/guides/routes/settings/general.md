# Route: `/settings/general`

**Page:** `apps/web/app/pages/settings/general.vue` · **Layout:** `default` · **Access:** signed in; rename needs owner or admin

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Rename | acceptance.spec.ts | 1 to 120 plain-text characters | Done | Unsaved-changes guard |

## Overview

Workspace name and type.

## User-facing knowledge

Owners and admins can rename the workspace. Everyone else sees the name read-only.

**Common user questions**

- **Can I change a personal workspace into a team?** Not yet. Create a new team workspace from the switcher.

## Form

Name field, Save. Leaving with unsaved edits asks first.

## API reference

| Call | Purpose |
| --- | --- |
| `PATCH /api/v1/workspace` | Rename; audited as `workspace.renamed` |

## Implementation map

`pages/settings/general.vue`; i18n `workspace.*`.
