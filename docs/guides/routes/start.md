# Route: `/start` (guided setup)

**Page:** `apps/web/app/pages/start.vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Stepper | Done | n/a | Documented | Six steps; any step is clickable |
| Resume | Done | 20+ characters for paste | Documented | Text is read in the browser; AI is optional |
| Basics | Done | name optional | Documented | Saved to the profile on finish |
| Quick answers | Done | defaults prefilled | Documented | Seeds the four common questions |
| First search | Done | optional | Documented | Calls `/tracks/plan` before creating |
| How we help | Done | n/a | Documented | Default Find and prepare |
| AI | Done | n/a | Documented | Opens AI settings in a new tab |

## Behavior

One linear flow replaces the scattered checklist links. Each step has a recommended path and a skip.

1. **Your resume**: upload a text or markdown file (read in the browser), paste text, read a PDF with AI, or start blank. The upload path never blocks on an AI key: pasted text is parsed with local heuristics for name, title, location, and skills.
2. **Basics**: name, current title, location, top skills. Prefilled from step 1.
3. **Quick answers**: work authorization, notice period, salary expectation, relocation, prefilled with safe defaults.
4. **First search**: one sentence. **Continue** calls `POST /api/v1/tracks/plan`; the criteria are saved with the search.
5. **How we help**: Find only, Find and prepare (Recommended), Fill forms for me.
6. **Turn on AI**: free provider, own key, or continue without AI. The step explains what works without AI.

**Start searching** creates or updates the profile, seeds the answer bank and the four answers, creates the search with the chosen autonomy, adds the recommended schedule (every 4 hours, quiet 22:00 to 07:00, 12 a day), then lands on `/tracks/:id`.

## Save paths

| Action | API | Effect |
| --- | --- | --- |
| Finish | `PATCH /profiles/{id}` | display name, headline, location, timezone |
| Finish | `POST /profiles/{id}/answers/setup` | seeds canonical answers, does not overwrite |
| Finish | `POST /profiles/{id}/answers` or `PATCH .../answers/{answer_id}` | the four quick answers |
| Finish | `POST /tracks` | search with criteria and autonomy |
| Finish | `POST /tracks/{id}/schedules` | recommended schedule |

## Edge cases

- No AI key: everything works except PDF reading; the page says so and offers paste.
- Plan call fails: the error is shown and the search is not created.
- Profile save fails: the flow stops with a toast; no partial search is created.
- Answer seeding fails: the flow continues, since answers are optional.

## Implementation map

`start.vue`, `useActiveProfile`, i18n `start.*`.


## Update (2026-11-13)

Resume reading now calls `POST /api/v1/onboarding/plan`, so the rule-based parser is shared by every client. The response also carries answer drafts for the four quick answers when a profile exists.
