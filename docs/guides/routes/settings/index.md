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
| Workspace | General, Members, Job alert emails, Connect AI, Connections | Everyone |
| Account | Your profile, Sign-in and devices, Notifications | Everyone |
| Admin | Source health, System status, Activity | Owner or admin |
| (no group) | Danger zone | Everyone; destructive actions need owner |

- Workspace holds settings that belong to the workspace. Account holds settings that follow you across workspaces.
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

## UX clarity (2026-11-13)

Sections are grouped the way people search for them: **Workspace** (general, members, job alert emails, connect AI, connections), **Account** (your profile, sign-in and devices, notifications), **Admin** (source health, system status, activity), then Danger zone. Workspace settings change the team; account settings follow the person. The mobile control is a sheet titled Settings; the trigger names the current section so the location never disappears. Each page presents its content in section cards, one primary action, and a save button that stays disabled until something changed.
