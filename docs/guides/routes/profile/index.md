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

## UX clarity (2026-11-12)

- Tabs are **Profile**, **Answers**, **Writing style**, **Files**.
- A completeness bar names the next three things to add and links to them.
- Evidence chips read **Proof from your resume** or **Our guess**, never strong/weak.
- The profile drawer is **Strengthen your profile**.

## Profile facets

The page shows cuisine, kitchen type, station, and covers definitions from the workspace's enabled field packs. Each value is a `profile_facets` row; add or remove it inline. Evidence refs for tailoring use `facet:<id>`. Facets are optional; an empty section is not an error.

API: `GET/POST /api/v1/profiles/{id}/facets`, `PATCH/DELETE /api/v1/profiles/{id}/facets/{item_id}`.


## Resume output

Base resumes include certifications, projects, and languages. Section order and headings follow the Track's industry pack: Hospitality puts Food safety certificates first and uses Kitchen skills and Signature dishes and menus. The pack template id is recorded on the resume version.