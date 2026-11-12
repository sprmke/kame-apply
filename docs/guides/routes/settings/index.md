# Route: `/settings`

**Page:** `apps/web/app/pages/settings.vue` · **Layout:** `default` · **Access:** signed in; Admin group needs owner or admin

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Grouped sub-nav | — | — | Documented | Grouped by scope, not by role |
| Mobile section picker | — | — | Documented | Current section + group list |
| Danger zone entry | — | — | Documented | Set apart at the end of the nav |

## Overview

`/settings` redirects to `/settings/general`. Every settings page renders inside this shell: a grouped sub-nav on desktop and one current-section control below `lg`. The shell decides nothing about the page content; each page owns its form, save path, and role checks.

## Navigation

| Group | Sections | Who sees it |
| --- | --- | --- |
| Workspace | General, Members, AI providers, Integrations, Notifications, Alerts | Everyone |
| Admin | Sources, Ops, Activity | Owner or admin |
| Account | Profile, Sessions | Everyone |
| (no group) | Danger zone | Everyone; destructive actions need owner |

- Desktop (`xl` and up): sticky left column, active item as a brand-50 pill with brand-700 text, matching the app rail.
- Below `xl`: a single row reading `Settings / <section>`. It opens the same groups in a sheet (88dvh, own scroll, backdrop). The sheet closes on selection, on the close control, or on Escape.
- No horizontal tab strip and no hidden overflow: every section is reachable without swiping.

## User-facing knowledge

Settings holds workspace setup, connections, notification choices, and account preferences. Members see the workspace and account groups. Owners and admins also see Admin.

**Common user questions**

- **Where do I delete a workspace?** Danger zone, last item in the settings nav.
- **Why can't I see Sources or Ops?** Those are admin views.

## API reference

None of its own; each child page calls its own endpoints.

## Implementation map

`apps/web/app/pages/settings.vue`; groups defined in the page script; i18n `settings.*`, `shell.workspace`, `shell.account`. Child routes documented in the neighbouring files.
