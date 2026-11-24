# Route guides

One guide per app route, kept in the same change as the page. Copy `../_template.md` for new routes.

| Route | Guide | Status |
| --- | --- | --- |
| `/login` | [login.md](./login.md) | Documented (Phase 2) |
| `/register` | [register.md](./register.md) | Documented (Phase 2) |
| `/verify-email?token=` | [verify-email.md](./verify-email.md) | Documented (Phase 2) |
| `/forgot-password` | [forgot-password.md](./forgot-password.md) | Documented (Phase 2) |
| `/reset-password?token=` | [reset-password.md](./reset-password.md) | Documented (Phase 2) |
| `/invite?token=` | [invite.md](./invite.md) | Documented (Phase 2) |
| `/` (Today) | [index.md](./index.md) | Documented (UX clarity, 2026-11-12) |
| `/start` | [start.md](./start.md) | Documented (setup from a resume, 2026-11-13) |
| `/help` | [help.md](./help.md) | Documented (UX clarity, 2026-11-12) |
| `/needs-you` | [needs-you.md](./needs-you.md) | Documented (UX clarity, 2026-11-12) |
| `/applications` | [applications.md](./applications.md) | Documented (Phase 11) |
| `/applications/:id` | [applications/detail.md](./applications/detail.md) | Documented (Phase 11 + 15–16 + 20) |
| `/responses` | [responses.md](./responses.md) | Documented (auto-match, no ids, 2026-11-12) |
| `/coach` | [coach.md](./coach.md) | Documented (People I help, 2026-11-12) |
| `/contacts` | [contacts.md](./contacts.md) | Documented (paste anything, 2026-11-12) |
| `/answers` | [answers.md](./answers.md) | Documented (Phase 12) |
| `/settings` | [settings/index.md](./settings/index.md) | Documented (grouped sub-nav, 2026-11-12) |
| `/settings/general` | [settings/general.md](./settings/general.md) | Documented (Phase 2) |
| `/settings/members` | [settings/members.md](./settings/members.md) | Documented (Phase 2) |
| `/settings/ai` | [settings/ai.md](./settings/ai.md) | Documented (connect hero, 2026-11-12) |
| `/settings/integrations` | [settings/integrations.md](./settings/integrations.md) | Documented (plain words, 2026-11-12) |
| `/legal/extension-privacy` | [legal/extension-privacy.md](./legal/extension-privacy.md) | Documented (Phase 13) |
| `/legal/privacy` | [legal/privacy.md](./legal/privacy.md) | Documented (Phase 14) |
| `/legal/terms` | [legal/terms.md](./legal/terms.md) | Documented (Phase 14) |
| `/legal/data-deletion` | [legal/data-deletion.md](./legal/data-deletion.md) | Documented (Phase 14) |
| `/settings/ops` | [settings/ops.md](./settings/ops.md) | Documented (Phase 14) |
| Extension side panel | [extension-sidepanel.md](./extension-sidepanel.md) | Documented (Phase 13) |
| `/settings/activity` | [settings/activity.md](./settings/activity.md) | Documented (Phase 2) |
| `/settings/danger` | [settings/danger.md](./settings/danger.md) | Documented (Phase 2) |
| `/settings/profile` | [settings/profile.md](./settings/profile.md) | Documented (Phase 2) |
| `/settings/sessions` | [settings/sessions.md](./settings/sessions.md) | Documented (Phase 2) |
| `/_design` | [_design.md](./_design.md) | Documented (Phase 2) |
| `/profile` | [profile/index.md](./profile/index.md) | Documented (Phase 3) |
| `/profile/answers` | [profile/answers.md](./profile/answers.md) | Documented (Phase 3) |
| `/profile/voice` | [profile/voice.md](./profile/voice.md) | Documented (Phase 3) |
| `/profile/documents` | [profile/documents.md](./profile/documents.md) | Documented (Phase 3) |
| `/profile/onboarding` | [profile/onboarding.md](./profile/onboarding.md) | Documented (Phase 3) |
| `/profile/review/:documentId` | [profile/review.md](./profile/review.md) | Documented (Phase 3) |
| `/profile/merge/:documentId` | [profile/merge.md](./profile/merge.md) | Documented (Phase 3) |
| `/tracks` | [tracks/index.md](./tracks/index.md) | Documented (Searches, new-search sheet, 2026-11-12) |
| `/tracks/:id` | [tracks/detail.md](./tracks/detail.md) | Documented (Matches tab, 2026-11-12) |
| `/tracks/:id/look-for` | [tracks/detail.md](./tracks/detail.md) | Documented (criteria view, 2026-11-12) |
| `/tracks/:id/improve` | [tracks/gaps.md](./tracks/gaps.md) | Documented (gap plan + Be Found, 2026-11-12) |
| `/tracks/:id/be-found` | [tracks/be-found.md](./tracks/be-found.md) | Documented (Phase 18) |
| `/tracks/:id/gaps` | [tracks/gaps.md](./tracks/gaps.md) | Documented (Phase 20) |
| `/tracks/:id/settings` | [tracks/settings.md](./tracks/settings.md) | Documented (Automation, recommended defaults, 2026-11-12) |
| `/tracks/:id/runs` | [tracks/runs.md](./tracks/runs.md) | Documented (History, stacked table, 2026-11-12) |
| `/notifications` | [notifications.md](./notifications.md) | Documented (Inbox, 2026-11-12) |
| `/settings/notifications` | [settings/notifications.md](./settings/notifications.md) | Documented (Phase 10) |
| `/settings/alerts` | [settings/alerts.md](./settings/alerts.md) | Documented (Phase 17) |
| `/settings/sources` | [settings/sources.md](./settings/sources.md) | Documented (Phase 5) |
| `/jobs` | [jobs.md](./jobs.md) | Documented (chips, why-this-match, mobile bar, 2026-11-12) |
| `/safety` | [safety.md](./safety.md) | Documented (Phase 7) |
| `/studio` | [studio.md](./studio.md) | Documented (plain tabs, auto-open, 2026-11-12) |
| `/tailor/:trackJobId` | [tailor.md](./tailor.md) | Documented (three steps, 2026-11-12) |

Advanced tools live under **Tools**. `/runs` redirects to `/tracks`; per-search history is `/tracks/:id/runs`. Answer Desk landed in Phase 12; applications in Phase 11; Phase 9 still creates application rows via Tailor Accept.

## Loading behavior

Every data route uses a layout-matched skeleton while its first request is pending: the same card, list row, table, or panel shape that the content will occupy, at 375, 820, and 1440. Static chrome (titles, tabs, filters) renders immediately. Filter changes keep the previous rows instead of collapsing to a skeleton, and an empty state appears only after the request resolves. The shared rules and components are in [`docs/design/design-system.md`](../../design/design-system.md#loading-and-skeletons-2026-11-23).
