# Full review: phases 0–20

Date: 2026-11-03. Scope: every phase marked Done in [`../phases/README.md`](../phases/README.md), reviewed for correctness, safety, maintainability, production readiness, and test coverage.

## Method

1. Ran the full quality gate and the API/runner test suites to get a baseline (coverage, failures, lint, types).
2. Read each phase file against its implementation and tests, grouped by area (0–2, 3–5, 6–9, 10–13, 14–20).
3. Verified every reported defect in the code before changing anything.
4. Fixed defects in priority order (P0 safety/tenancy/truthfulness first), adding a test for each fix.
5. Re-ran the gate and the suites.

## Baseline

| Check | Before | After |
| --- | --- | --- |
| `pnpm run ci:quality` | Failed on untracked agent tooling (stack-terminology, prettier) | Passes end to end |
| API tests | 490 passed, 1 failed (date-rotted schedule test) | 520 passed, 3 skipped |
| Evals (deterministic) | Not run by the gate | 101 passed, 1 skipped |
| API line coverage | 66% | 66% (17,687 statements; new code is covered at the same rate) |
| Runner tests | 2 files, no submit-gate coverage | 3 files, 12 tests incl. real Chromium submit-gate |
| Web unit tests | 2 files | 4 files, 13 tests |
| Extension unit tests | 2 files | 3 files, 7 tests |

## P0 fixes (safety, tenancy, truthfulness)

### The tenancy guard was silently disabled

`apps/api/tests/test_route_coverage.py` iterated `app.routes` and skipped everything that was not an `APIRoute`. FastAPI 0.162 stores `include_router` results as lazy `_IncludedRouter` wrappers, so the guard saw **zero** of the 289 v1 routes and passed vacuously. It now expands `effective_candidates()` recursively, asserts it reaches the whole tree, and treats the runner/extension context providers as valid scoping roots (they resolve the workspace from a token instead of `X-Workspace-Id`).

### Workspace export leaked the global job corpus

`GET /workspace/export` ran `SELECT * FROM jobs`. `jobs` is a global table with no RLS, so any signed-up user could download every posting from every workspace. Jobs are now exported only through the caller's `track_jobs` rows. `workspace_members` is filtered by `workspace_id` (membership RLS intentionally exposes a user's other workspaces). Test: `test_export_does_not_leak_global_jobs_or_other_memberships`.

### The runner could submit without a human decision

`input[type=submit]` was in `Adapter.next_selectors` and clicked on every loop iteration, before the `final_review` check. It is removed; Next/Continue clicks now go through `click_next`, which reads the control's label and refuses Submit/Send application/Apply now. Real-browser tests cover a submit-only form, a Next input, and a submit-labelled button. The same change tightens confirmation needles (no generic "thank you"), CAPTCHA detection (visible widget only, not a script tag), and login detection (visible password input).

### Submit approval and completion ignored policy

`approve_submit` set `submit_approved` on any checkpoint kind and ignored `allow_submit`; `complete(confirmation=true)` only checked `submit_approved`. Now: approval is accepted only on a `final_review` checkpoint, and only when `policy.allow_submit` is true (assist runs hand off to the human). Completion with confirmation requires both. A runner token may only finish the run it claimed.

### Sensitive typed values were persisted

`resolve_checkpoint` stored the typed SSN-class value in `apply_runs.policy`, where it survived a dead runner. Values now live in a process-local one-shot vault (`app/runs/ephemeral.py`, 5 minute TTL), are removed on read, and are readable only with a runner credential (a browser session gets 403). Tests assert the raw value is absent from the persisted row.

### Live view let a read-only member take over

The live token always carried `role="viewer"`, and the WebSocket accepted `takeover`/`input`/`paste` from any token. Tokens now carry the real workspace role, the socket re-checks active membership, and control messages from roles without `data.write` are refused.

### Answer Desk invented eligibility claims

A yes/no question containing "authorized" always drafted "Yes", and behavioral questions produced a canned story attributed to the user's real employer. Yes/no now answers only from `work_authorization` (and asks otherwise); behavioral questions return `needs_story`. Tests cover both, including the profile-fact path.

### Resume truthfulness

- The verifier only checked numbers and six stock phrases. It now also rejects a profile skill named on a line whose own evidence does not contain it, and named entities with no profile evidence.
- The base resume used the job title / Track name as the candidate's headline and summary. It no longer does.
- `propose_improvements` prepended the target role to the profile summary. It now only reuses the profile's own text.
- Tailoring appended posting terms to the first available bullet (`"Managed the rota (Kubernetes)."`). That path is removed; tailoring only surfaces evidenced skills and reports gaps.
- CSV export is formula-injection safe (`=`, `+`, `-`, `@` get a leading apostrophe).
- The parse gate fell back to the source text when PDF extraction returned nothing, so a corrupt/scanned file passed. It now fails with `unreadable_file`. The `broken` dev flag is rejected in production, and a storage failure returns 502 instead of an object key dressed up as a URL.
- PDF export truncated every line at 110 characters; it now wraps.

### SSRF and untrusted URLs

Job/apply URLs from feeds, clips, inbound email, and applications are checked against a literal private-address guard (`is_public_http_url_literal`), and the push sender refuses non-public endpoints. The runner preflight also rejects a private apply URL.

### Webhook fail-open

The Telegram webhook only verified its secret when one was configured, and inbound email accepted unsigned callbacks in `dev`. Both now fail closed outside local/test, and production refuses to start with the Telegram bot enabled and no webhook secret.

### Extension token exfiltration

The extension accepted any `apiBase` from a `kame.connect` message; a look-alike origin could redirect the token and clipped page content. It now allowlists our API origins, requires a `ka_ext_` token, and rejects untrusted handshakes loudly. The extension also stops reading SSN/bank/card/DOB values (by label, name, and autocomplete token), and clips no longer store page prose in the shared job corpus.

## P1 fixes (correctness and production readiness)

| Area | Fix |
| --- | --- |
| Recruiter Lens | `work_authorization` is loaded (knockouts can fire); country comes from authorization, not the first two letters of the city; skill matching is normalized equality (`Java` no longer matches `JavaScript`); an empty skills section no longer grades everything "met"; overlapping roles no longer double-count years. |
| AI budget | Every model call, including `POST /ai/credentials/{id}/test`, passes the budget guard; a budget stop is surfaced (402) instead of being reported as an invalid key. |
| Config | `MASTER_KEK` is validated at startup (base64, 32 bytes); `.env.example` documents every Phase 14–19 secret. |
| Auth | Logout writes `auth.session_revoked`; an orphaned refresh token returns 401 instead of 500. |
| Audit | Pagination uses a `(created_at, id)` cursor (`before_id` / `next_before_id`) so rows sharing a timestamp are not dropped. |
| Notifications | Push/Telegram cells can be saved (migration 0034); Needs-you class events fan out to push and Telegram; Web Push is real (`pywebpush`) with VAPID keys; the digest fires in one minute of the day, not two. |
| Scheduling | Deployed environments run a minute scheduler (`app/schedules/scheduler.py`) that reaches every workspace through a security-definer id helper; two active runs no longer raise `MultipleResultsFound`; the tick endpoint is always workspace-scoped. |
| Discovery | A bad record rolls back to a savepoint instead of the whole run; a failed run is persisted with `status=failed`; dedupe considers location; generated directory slugs are `candidate` (never polled) instead of pretending to be validated boards. |
| Logging | Redaction recurses into nested dicts and lists. |
| MCP bridge | `propose_resume_changes` persists verified drafts as `ResumeChange` rows; `submit_answers` writes answer drafts and refuses AI-restricted items; `log_application` and `update_application_status` update the tracker. The test now calls the real verifier instead of re-implementing it. |
| CI | Runner browser tests, evals, token contrast, design-slop, and the untrusted-prompt check now run in GitHub Actions. |
| Deploy/backup | The backup loop requires the owner role, verifies the dump, prunes to the retention counts, and exits after three consecutive failures; `deploy:api` transfers the image when no registry is configured and can run a health check. |
| Web | Legal pages are public (OAuth review needs them); the activity list passes the compound cursor. |

## Follow-up pass (2026-11-04)

- Tailoring: each proposal is a `resume_changes` row with Keep/Remove; the draft is rebuilt from the base resume and the Lens is recomputed.
- Discovery: run-now is queued in deployed environments, the worker commits progress per board/source, the Track page polls until done, and Layer-2 feeds close missed jobs. Career pages check `robots.txt`.
- Runner: image and Compose service, `deploy:runner:*`, heartbeat reaper (requeue then fail), resume attachment from a signed URL, blurred screenshots stored in R2, and a deploy health check.
- LLM: `resume_tailor_review.v1` adds advisory notes; the deterministic Lens stays authoritative.
- Operations: the minute scheduler takes a Postgres advisory lock, reaps lost runs, and hard-deletes workspaces after 30 days. Track duplicate copies source choices and settings. Runner preflight warns on the company cap instead of blocking.
- Extension: an Answer button inserts a drafted answer into the focused field; the clip risk banner reads `job_risk`.

## Known gaps (not fixed in this pass)

These are real and documented in the phase files rather than silently claimed done:

- Resume critique, the cover letter, and the tailor reviewer call their LLM prompts with a deterministic fallback (and a sentence-level verifier for letters). The Lens stays deterministic for consistent grading.
- Tailoring keeps or removes each change and rebuilds the draft, but the run is still synchronous in the request (no streamed progress).
- Board crawling now checks `robots.txt`; conditional requests are supported by the HTTP client but not wired into the board poller.
- Per-ATS account steps and skip-filled-on-resume are missing from the runner.
- Auto-submit is policy-only; the runner always pauses at `final_review`.
- Web push needs operator VAPID keys; without them it logs and sends nothing.
- The in-app notification stream is a one-frame snapshot, not a live socket.
- Coverage hot spots below 50%: `tracks/service.py`, `workspaces/service.py`, `strategy/service.py`, `taxonomy/normalize.py`, `tracks/geocode.py`.

## Verification

```bash
pnpm run ci:quality      # passed: tooling, lint, format, types, build, 520 API tests, 12 runner tests, api-client drift, 13 web tests, 101 evals
pnpm exec playwright test e2e/shell.spec.ts e2e/career-profile.spec.ts e2e/tracks.spec.ts   # 12 passed
```

The earlier e2e run failed only because a stale API process without `AUTH_RATE_LIMIT_ENABLED=false` was reused by Playwright; with a clean server all 12 core specs pass.

Remaining coverage hot spots (below 50%): `tracks/service.py`, `workspaces/service.py`, `strategy/service.py`, `taxonomy/normalize.py`, `tracks/geocode.py`. They have API-level tests for their main flows but many branches (limits, emails, duplicates, backfills) are still untested.
