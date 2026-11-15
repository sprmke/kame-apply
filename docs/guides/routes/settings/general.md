# Route: `/settings/general`

**Page:** `apps/web/app/pages/settings/general.vue` · **Layout:** `default` · **Access:** signed in; rename needs owner or admin

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Rename | acceptance.spec.ts | 1 to 120 plain-text characters | Done | Save stays disabled until changed; unsaved-changes guard |
| Type | Manual | n/a | Done | Read-only chip |
| Set up from a resume | Pending | same draft rules as `/start` | Done | Opens `/start`; update mode when the profile has facts |

## Overview

Workspace name and type, in one section card. The intro line states the permission: only owners and admins can rename it. A second card opens setup from a resume.

## User-facing knowledge

Owners and admins can rename the workspace. Everyone else sees the name read-only and no Save button. Any member can start setup from a resume; a viewer is refused by the API.

**Common user questions**

- **Can I change a personal workspace into a team?** Not yet. Create a new team workspace from the switcher.

## Form

Type chip (read only), Name field, Save. Save appears disabled until the name differs from the saved value. Leaving with unsaved edits asks first. **Set up from a resume** is one line and one button.

## API reference

| Call | Purpose |
| --- | --- |
| `PATCH /api/v1/workspace` | Rename; audited as `workspace.renamed` |

## Implementation map

`pages/settings/general.vue`; i18n `settings.general*`, `workspace.*`; `FnSectionCard`.
