# Route: `/settings/general`

**Page:** `apps/web/app/pages/settings/general.vue` · **Layout:** `default` · **Access:** signed in; rename needs owner or admin

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Rename | acceptance.spec.ts | 1 to 120 plain-text characters | Done | Save stays disabled until changed; unsaved-changes guard |
| Type | Manual | n/a | Done | Read-only chip |
| Set up from a resume | Pending | same draft rules as `/start` | Done | Opens `/start`; update mode when the profile has facts |
| Fields of work | manual + API | curated pack keys | Done | Owner/admin; preview before primary change |

## Overview

Workspace name and type, in one section card. The intro line states the permission: only owners and admins can rename it. A second card opens setup from a resume. **Fields of work** sits under it and chooses the workspace default: the primary field for new searches and the union of fields that Profile, Answers, and Today draw from.

## User-facing knowledge

Owners and admins can rename the workspace. Everyone else sees the name read-only and no Save button. Any member can start setup from a resume; a viewer is refused by the API.

Owners and admins can add another curated field, remove one, or make an extra field primary. Changing the primary shows one line of consequence first ("New searches default to Hospitality and food. Shift filters appear in searches."), then confirms. Removing a field never deletes data: searches using it move to General and the person can still use General.

**Common user questions**

- **Can I change a personal workspace into a team?** Not yet. Create a new team workspace from the switcher.
- **Why is General always listed?** It is the fallback for any search. It is not a stored choice and cannot be removed.
- **Do two fields conflict?** No. Shared pages show the union of the workspace's fields; each search uses one field.

## Form

Type chip (read only), Name field, Save. Save appears disabled until the name differs from the saved value. Leaving with unsaved edits asks first. **Set up from a resume** is one line and one button. Fields of work: primary badge, Make primary, Delete, and add buttons for curated fields not yet enabled. The preview appears inline before a primary change.

## API reference

| Call | Purpose |
| --- | --- |
| `PATCH /api/v1/workspace` | Rename; audited as `workspace.renamed` |
| `GET /api/v1/workspace/industries` | Enabled fields plus General |
| `POST /api/v1/workspace/industries` | Add a field; `workspace.update` |
| `PUT /api/v1/workspace/industries/primary` | Change primary; `workspace.update` |
| `DELETE /api/v1/workspace/industries/{key}` | Remove a field; tracks move to the remaining primary or General |
| `GET /api/v1/workspace/experience` | Resolved manifests for the UI |

## Implementation map

`pages/settings/general.vue`; i18n `settings.general*`, `workspace.*`; `FnSectionCard`.
