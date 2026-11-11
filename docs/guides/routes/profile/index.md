# Route: `/profile`

**Page:** `apps/web/app/pages/profile/index.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Career header + experiences | Yes | API | Documented | Interview drawer + upload CTA |
| Answer bank / Voice / Documents tabs | Yes | API | Documented | Nested under `/profile/*` |

## Overview

Career Profile hub: facts from resume parse/confirm, interview proposals, and section navigation. The page lede explains that these facts feed matches and drafts; the experience section explains strong versus weak evidence.

## User-facing knowledge

This is your source of truth for applications. Upload a resume, confirm the parse, then fill the answer bank and voice samples.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/profiles` | list / pick default |
| `GET /api/v1/profiles/{id}` | full profile |
| Interview + documents routes | see architecture/profile.md |

## Implementation map

`useActiveProfile`, `InterviewDrawer`, i18n `career.*`.
