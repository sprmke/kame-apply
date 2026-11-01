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
| `GET /api/v1/runs/{id}/ephemeral-sensitive` | runner | One-shot sensitive value; cleared |
| `POST /api/v1/runs/{id}/complete` | runner | Finish; confirmation requires `submit_approved` |
| `POST /api/v1/runs/{id}/handoff` | member | Pause + open URL for extension |

Auth: JWT session or runner bearer (`ka_run_…`) + `X-Workspace-Id`. Never trust client `workspace_id` in the body.

## Policy

- LinkedIn / Indeed / JobStreet: `platform_no_auto_submit`; `allow_submit` forced false.
- Submit click only after `final_review` → `approve_submit` sets `submit_approved`.
- Sensitive typed values live only in ephemeral policy blob; never in `activity_log` or checkpoint.decision.

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
