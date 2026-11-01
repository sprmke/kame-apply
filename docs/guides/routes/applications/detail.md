# Route: `/applications/:id`

**Page:** `apps/web/app/pages/applications/[id].vue` · **Layout:** `default` · **Access:** signed in

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Header / status | — | transition + note | Documented | Phase 11 |
| Runner / checkpoints | — | preflight + decisions | Documented | Phase 15 |
| Live view / takeover | — | run-scoped live token | Documented | Phase 16 |
| Timeline | — | — | Documented | events |
| Follow-up draft | — | — | Documented | copy only |
| Posting snapshot | — | — | Documented | R2 or live |
| Notes | — | max length | Documented | |
| Answer Desk | — | — | Documented | Phase 12 attached answers |
| Interview prep | — | profile evidence only | Documented | Phase 20b |
| Referrals | — | contacts match | Documented | Phase 20e |

## Overview

Application dossier: status control, **Apply with runner** (queues a cloud/local Playwright run), live canvas with take over / hand back, open checkpoint actions, step log (replay markers), follow-up draft, interview prep, referral matches/drafts, timeline, posting text, Answer Desk answers, notes.

## User-facing knowledge

Change status from the select. Use **Apply with runner** when the application is ready and a resume is attached. Resolve checkpoints (continue, skip, type a sensitive value once, approve submit) from this page or Needs you. **Continue in browser** hands the URL to you/the extension.

## API reference

| Call | Purpose |
| --- | --- |
| `GET /api/v1/applications/{id}` | Detail |
| `PATCH /api/v1/applications/{id}/status` | Status |
| `PATCH /api/v1/applications/{id}/notes` | Notes |
| `GET /api/v1/runs?application_id=` | Runs for this application |
| `POST /api/v1/runs/runner/start` | Queue runner |
| `GET /api/v1/runs/{id}/checkpoints` | Checkpoints |
| `POST /api/v1/runs/checkpoints/{id}/resolve` | Resolve |
| `GET /api/v1/runs/{id}/steps` | Step log |
| `POST /api/v1/runs/{id}/handoff` | Extension handoff |
| `POST /api/v1/runs/{id}/live/token` | Mint live viewer token |
| `WS /api/v1/runs/{id}/live` | Frame + input relay |
| `GET/POST /api/v1/applications/{id}/interview-prep` | Interview prep |
| `GET /api/v1/applications/{id}/referral-matches` | Contact matches |
| `POST /api/v1/applications/{id}/referral-drafts` | Outreach draft |
| `POST /api/v1/runs/{id}/live/takeover` | Take control |
| `POST /api/v1/runs/{id}/live/handback` | Return control |

## RBAC

`data.read` for detail and run reads; `data.write` for status, notes, start, resolve, handoff.

## Implementation map

`apps/web/app/pages/applications/[id].vue` · `apps/web/app/components/LiveViewCanvas.vue` · `apps/api/app/applications/tracker.py` · `apps/api/app/runs/` · `docs/architecture/apply-runner.md` · `docs/architecture/live-view.md`
