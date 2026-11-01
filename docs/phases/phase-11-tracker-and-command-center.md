# Phase 11: Applications tracker & command center

**Status:** Done · **Release:** R1 · **Depends on:** 10 · **Features:** F11 · **Reference:** [`design/ux-blueprint.md`](../design/ux-blueprint.md) §3.1, §3.6

## Goal

Full management of every application and a home screen that shows status, results, risks, and what needs the user, at a glance, on any device.

## Acceptance scenarios

1. Home shows the Needs-you strip, KPI tiles (period selector), Track cards, activity feed, upcoming runs/reminders; empty-state checklist for new users.
2. Applications page: table + kanban across Tracks; drag to change status (mobile: status picker); filters by Track/status/date/method; saved views.
3. Application detail: timeline (created, tailored, submitted, status changes), frozen job snapshot (viewable even after the posting disappears), files sent, answers, notes, reminders.
4. Log a manual application in two clicks from a job ("I applied on the company site") or create one from scratch (company + title + URL).
5. Follow-up reminder at N days after submission (default 7) with a drafted follow-up the user copies (never sent automatically).
6. KPIs: discovered, matched, shortlisted, submitted (today/week/total), response rate, interview rate, per Track and overall; funnel chart.

## Tasks

- [x] Status state machine with allowed transitions and timestamps: `ready → in_progress → needs_you → submitted → responded → interview → offer | rejected | withdrawn | ghosted` (ghosted auto-suggested after N days without response, user confirms).
- [x] Job snapshot at submit/mark-applied: sanitized HTML + metadata to R2.
- [x] Applications API (list with filters/pagination, detail, update status, notes, reminders), events table.
- [x] Metrics service (materialized daily aggregates per workspace/Track) for KPIs and funnel.
- [x] Home page components per blueprint §3.1; Track overview tab with pipeline mini-bar.
- [x] **Outcome analytics** (feedback loop): response and interview rate broken down by method (extension/runner/manual), tailored vs base resume, Lens grade at submit, source, freshness at apply, Track. Feeds ranking weights and Lens calibration; shown to the user as "what's working".
- [x] Cross-Track duplicate guard: applying to a job already applied (any Track) → warning.
- [x] Data export: applications CSV/JSON with files.

## Edge cases & failure modes

- Same company, multiple roles → grouped view by company; per-company count visible.
- User applied outside the app → manual log + later extension auto-log (Phase 13).
- Status regressions (interview → rejected → interview again) allowed with a note.
- Large histories (1,000+ applications) → server pagination + virtualized lists.
- Timezone of "today" = user's timezone.

## Testing

State machine unit tests; metrics correctness on fixtures; E2E: mark applied → status changes → KPIs update; mobile screenshots.

## Docs to update

Route guides (home, applications), `docs/architecture/applications.md` (new).

## Exit criteria

- [x] Scenarios 1–6 pass; design review at 375/820/1440 light/dark.
