# Route: `/_design`

**Page:** `apps/web/app/pages/_design.vue` · **Layout:** `none` · **Access:** dev and e2e builds only (404 in production unless `NUXT_PUBLIC_ENABLE_DESIGN=true`)

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Style guide | design.spec.ts (6 visual snapshots) | n/a | Done | Light and dark at 375/820/1440 |

## Overview

Living style guide: every component and state in the current theme.

## User-facing knowledge

For designers and developers. Update this page whenever a component or token changes.

**Common user questions**

- **How do I update the snapshots?** `pnpm exec playwright test e2e/design.spec.ts --update-snapshots`, review the diff, commit.

## Sections

Color, Type, Buttons, Forms, Chips and tabs, Overlays, Table and loading, Signature components.

## API reference

| Call | Purpose |
| --- | --- |
| none | Static |

## Implementation map

`pages/_design.vue`, `packages/ui/src/*`; tokens in `packages/ui/src/tokens.css`.
