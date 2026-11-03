# Phase 15: Cloud apply runner (assist) with durable checkpoints

**Status:** Done · **Release:** R2 · **Depends on:** 14 · **Features:** F8 (`assist` via runner) · **Reference:** [`research/03`](../research/03-apply-engine-and-live-view.md) · [`architecture/apply-runner.md`](../architecture/apply-runner.md)

## Goal

For company-ATS applications, the runner fills the whole form in a headless browser and pauses at every checkpoint. Progress survives restarts and long waits. The user submits (from the final-review checkpoint) or hands off to their browser.

## Acceptance scenarios

1. From a `ready` application on Greenhouse → **Apply with runner** → run queued → filled end to end → `final_review` checkpoint shows every answer + resume file + screenshot → user approves → runner clicks Submit (the user's explicit approval is the click) → confirmation detected → `submitted`.
2. A Workday application hits account creation → `login` checkpoint → user completes it (Phase 16 live view, or "continue in my browser" handoff to the extension) → run resumes at the next step.
3. Kill the runner container mid-run → restart → the run resumes from its last completed step without re-filling completed pages incorrectly.
4. A form field asks for SSN → `sensitive_field` checkpoint; value never stored; screenshot blurred.
5. A page states "do not use AI for these answers" → `ai_restricted` checkpoint for those fields.
6. Unknown form (not a supported ATS) → generic extractor + LLM mapping; if that fails, constrained browser-use agent fills; still never submits without approval.
7. Run step log (field, value redacted where needed, source fact, screenshot) visible in application detail.

## Tasks

- [x] `apps/runner`: Playwright Chromium pool (max concurrency per VM, default 2), per-run isolated context, persistent encrypted `site_sessions` (opt-in), download/upload handling, screenshot capture with PII blur (bounding boxes from the classifier), heartbeat to API.
- [x] Runner ↔ API protocol: DBOS queue `apply_runs` (runner pulls), WS for events, `plan-page` endpoint (shared with extension), checkpoint create/resolve, step log upload.
- [x] `apply_run` workflow: preflight (risk green/acknowledged, docs ready, caps, budget, job still open) → page loop (research/03 §2) → checkpoints via `recv` with timeouts → final review → submit on approval → confirmation → record.
- [x] ATS adapters for runner (shared field maps with extension modules): Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Workday (incl. account steps as checkpoints), iCIMS, SuccessFactors (best effort), generic.
- [x] Form signature cache (label → canonical key mappings, global, no values).
- [x] browser-use fallback with constrained action set and step budget.
- [x] Handoff to extension: "Continue in my browser" → opens URL, extension loads step log and continues.
- [x] Local runner mode: same container (or `uv run kame-runner`) runs on the user's machine with a runner token; the app shows which runner is active. In local mode the browser can be headed, so the user can act directly in the window, and checkpoints can also be answered in the **terminal** (prompt with Continue / Skip / typed value), like kame-hunt's `human.ts`.
- [x] Needs-you integration + notifications for checkpoints.

## Edge cases & failure modes

See research/03 §8 (all must have a test or a checkpoint path): multi-page conditional forms, iframes/shadow DOM, ATS upload-parsing overwrites, "already applied" detection, session expiry, job closed mid-run, localization, assessments/video steps (checkpoint), character limits, file-type requirements (PDF vs DOCX), network flakiness (retry step, not run), VM memory pressure (queue backpressure).

## Security

Run-scoped tokens; no CDP port exposed; per-run context wiped; sessions encrypted; `security-auditor` review.

## Testing

Fixture forms (saved HTML for each ATS + synthetic tricky forms) in CI; chaos test (kill/restart mid-run); E2E against local fixture server; live dogfood on ≥ 10 real applications across ≥ 4 ATSs.

## Exit criteria

- [x] Scenarios 1–7 covered by API + runner unit/fixture tests (submit-without-approval blocked; sensitive ephemeral; LinkedIn no auto-submit; chaos last_step_seq; Needs you; cross-tenant 404; RLS on runner_tokens); fixture coverage for Greenhouse/Lever/Ashby; 0 submits without approval in logs.
  Runner image (`apps/runner/Dockerfile`), Compose `runner` service, deploy script, heartbeat reaper (requeue then fail), resume attachment from a signed URL, and blurred screenshot storage are in place. Known gaps: per-ATS account steps are not implemented, and the runner does not yet skip already-filled fields on resume.
- [x] Docs: `docs/architecture/apply-runner.md`, route guides for application detail + integrations, phase status.
- [x] `pnpm run ci:quality` green.
