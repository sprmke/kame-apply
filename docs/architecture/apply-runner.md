# Apply runner (Phase 15)

Cloud or local Playwright runner fills company-ATS forms and pauses at every checkpoint. The human owns Submit (and logins, CAPTCHAs, sensitive values).

## Protocol

| Call | Who | Purpose |
| --- | --- | --- |
| `POST /api/v1/runs/tokens` | owner/admin | Create `ka_run_…` token (once) |
| `POST /api/v1/runs/runner/start` | member | Preflight + queue `apply_run` |
| `POST /api/v1/runs/runner/claim` | runner | Pull oldest queued run (204 if none) |
| `POST /api/v1/runs/{id}/heartbeat` | runner | Liveness + page URL |
| `POST /api/v1/runs/{id}/plan-page` | runner | Shared plan-page brain (extension) |
| `POST /api/v1/runs/{id}/steps` | runner | Idempotent step log by `seq` |
| `POST /api/v1/runs/{id}/checkpoints` | runner | Open checkpoint → `needs_you` |
| `POST /api/v1/runs/checkpoints/{id}/resolve` | member or runner | Human decision (`DBOS.send` when configured) |
| `GET /api/v1/runs/{id}/ephemeral-sensitive` | runner token only | One-shot value from the process-local vault (5 min TTL); removed on read, never in Postgres |
| `POST /api/v1/runs/{id}/complete` | runner | Finish; confirmation requires `submit_approved` **and** `policy.allow_submit`; the runner may only finish the run it claimed |
| `POST /api/v1/runs/{id}/handoff` | member | Pause + open URL for extension |

Auth: JWT session or runner bearer (`ka_run_…`) + `X-Workspace-Id`. Never trust client `workspace_id` in the body.

## Policy

- LinkedIn / Indeed / JobStreet: `platform_no_auto_submit`; `allow_submit` forced false.
- Submit click only after `final_review` → `approve_submit` sets `submit_approved` (rejected on any other checkpoint kind, and when `allow_submit` is false: assist runs hand off to the human).
- Sensitive typed values live only in an in-memory one-shot vault (`app/runs/ephemeral.py`); never in `apply_runs.policy`, `activity_log`, or `checkpoint.decision`. The API must run one worker process for the runner hand-off.
- The minute scheduler reaps runs whose runner stopped heartbeating: after 5 minutes the run returns to `queued` (runner cleared) so another runner can resume from `last_step_seq`; after two attempts it is `failed` with `runner_lost`.
- `plan-page` returns a signed `resume_upload_url` for the accepted resume; the runner downloads it and attaches it to visible file inputs. Blurred step screenshots are uploaded as base64, stored under `ws/<workspace>/runs/<run>/step-<seq>.png`, and listed with a signed `screenshot_url`.
- Navigation clicks are screened: a control whose label is Submit/Apply now is never clicked by the Next/Continue path, and `input[type=submit]` is not a Next selector.

## Local mode

```bash
export KAME_RUNNER_API_BASE=http://127.0.0.1:8100
export KAME_RUNNER_TOKEN=ka_run_…
export KAME_RUNNER_WORKSPACE_ID=…
export KAME_RUNNER_MODE=local
uv run kame-runner
```

Headed browser; checkpoints can be answered in the terminal or in the app.

## Fixtures

Saved HTML under `apps/runner/fixtures/` (Greenhouse, Lever, Ashby, sensitive, Workday login) for CI and dogfood.
