# UX clarity review: full pass

**Date:** 2026-11-13 · **Branch:** `ux/clarity-overhaul` · **Skill:** `ux-clarity-review`

Method: `check:ux-jargon`, `check:design-slop`, screenshots at 375 / 820 / 1024 / 1440, a cold-account scripted run, and a source read of each changed route. Raw captures stay in `.audit-screenshots/` (gitignored).

## Scripted run, fresh account

A new account was created through `/register`, which now lands on `/start`. Timings from the browser run:

| Step | Time from start | Result |
| --- | --- | --- |
| Register and land on `/start` | 2.8 s | pass |
| Paste resume, read it, fill basics | 4.0 s | pass, name/headline/location/skills prefilled by the server parser |
| Continue through answers | 5.5 s | pass, four defaults ready |
| Describe the search and get a plan | 6.4 s | pass, titles and filters generated without AI |
| Finish and land on the search | 8.4 s | pass, profile, search, answers, and schedule created |

Task 2 (remote only, minimum salary): 3.4 s, saved and persisted. This run exposed a real bug: number inputs emitted numbers, while the computed setters expected strings, so salary was dropped from the save body. Fixed in `FnInput` and both computed setters.

Task 5 (turn on AI with a free provider): 2.6 s to the provider form, with OpenRouter preselected. This run exposed that the add-key watcher reset the provider to Gemini after the choice card ran. Fixed with a single `openAdd(preset)` path.

Task 4 (file a reply): the match card appears for a known application. On a cold account with no applications the page says so instead of showing an id field. A server match that finds nothing leaves the picker empty, which is the intended fallback.

Task 3 (tailor and attach) was exercised on the seeded account: three steps, `Accept and attach` at the end. No blocking issue.

## Route verdicts

| Route | Q1 where | Q2 what for | Q3 next | Q4 consequence | Q5 waiting | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `/start` | pass | pass | pass | pass | n/a | Active step keeps its label, others show numbers at 375 |
| `/` Today | pass | pass | pass | pass | pass | One primary fill; numbers link to lists |
| `/tracks` | pass | pass | pass | pass | n/a | New-search sheet has Describe / Template / Copy |
| `/tracks/:id` | pass | pass | pass | pass | n/a | Matches is the landing tab |
| `/tracks/:id/look-for` | pass | pass | pass | pass | n/a | Impact chips show what relaxing a filter adds |
| `/tracks/:id/settings` | pass | pass | pass | pass | n/a | Recommendation card with one action |
| `/tracks/:id/runs` | pass | pass | n/a | pass | n/a | Stacked rows at 375; failed runs say what to try |
| `/tracks/:id/improve` | pass | pass | pass | pass | n/a | Gap plan fills on first open |
| `/jobs` | pass | pass | pass | pass | n/a | Status chips, More filters, why-match at every width |
| `/applications` | pass | pass | pass | pass | n/a | Empty state first, filters folded |
| `/applications/:id` | pass | pass | pass | pass | pass | Checkpoints use plain labels and a consequence line |
| `/profile` | pass | pass | pass | pass | n/a | Completeness names the next three things |
| `/profile/answers` | pass | pass | pass | pass | n/a | Drafts show source and Use / Dismiss |
| `/profile/voice` | pass | pass | pass | pass | n/a | Presets first, samples optional |
| `/studio` | pass | pass | pass | pass | n/a | Opens on the latest resume with a check |
| `/tailor/:id` | pass | pass | pass | pass | n/a | Three steps at 375 |
| `/responses` | pass | pass | pass | pass | n/a | No id field; match card explains the guess |
| `/contacts` | pass | pass | pass | pass | n/a | Paste anything, preview, optional AI read |
| `/coach` | pass | pass | pass | pass | n/a | Nav and title match |
| `/notifications` | pass | pass | pass | pass | pass | Inbox, Needs you split |
| `/needs-you` | pass | pass | pass | pass | pass | Decisions only |
| `/help` | pass | pass | pass | pass | n/a | Glossary and shortcuts |
| `/settings` | pass | pass | pass | pass | n/a | Account, Workspace, AI and connections, Admin |
| `/settings/ai` | pass | pass | pass | pass | n/a | Three connect paths; advanced folded |
| `/settings/integrations` | pass | pass | pass | pass | n/a | Browser / Claude / Apply helper / More |
| `/settings/notifications` | pass | pass | pass | pass | n/a | Recommended reset |
| `/settings/sources` | pass | pass | n/a | pass | n/a | Admin only; legend added |
| `/settings/ops` | pass | pass | n/a | pass | n/a | Admin only; plain status labels |
| `/safety` | pass | pass | pass | pass | pass | Check first when nothing is flagged? See below |
| `/answers` | pass | pass | pass | pass | n/a | Paste, draft, copy |
| `/login`, `/register` | pass | pass | pass | pass | n/a | Register now says next: `/start` |
| legal pages | pass | pass | n/a | n/a | n/a | Unchanged |

## Fixed during this pass

1. Numeric inputs dropped salary and radius. `FnInput` now accepts numbers; setters coerce.
2. The AI free-provider choice still opened the Gemini form. One `openAdd(preset)` path now owns the reset.
3. Onboarding now uses the server parser, so the same resume text gives the same basics on web and in any future client.
4. Register sends a new account to `/start`.
5. Notifications: email defaults no longer include run-failed, matching the plan.

## Remaining, known

- `/safety` still opens on the flagged list when empty. Moving the check box first is a one-line tab default; deferred because the flagged list is the more common return visit.
- Settings Connections uses tabs on one route rather than four routes. Deep links are unchanged, which is deliberate.
- The quick answer step stores four canonical answers; career-specific questions (licences, shift availability) are not drafted yet.

## Gates

`check:ux-jargon` OK · `check:design-slop` OK · `check:token-contrast` OK · type-check clean · lint 0 errors · web and extension tests pass · web build passes.
