---
name: ats-adapter
description: "How to add an ATS form adapter for the apply engine: detection, step model, field map, widgets, fixtures from saved HTML, checkpoint triggers. Phases 13/15."
---

# ATS adapter

Read `docs/research/03-apply-engine-and-live-view.md` and `.cursor/rules/apply-engine.mdc` first.

1. **Detect** by URL pattern and DOM signature (Greenhouse, Lever, Workable, Ashby, SmartRecruiters, Workday...). Detection must be cheap and side-effect free.
2. **Step model**: list the steps/pages and their transitions (next, review, submit). Never click submit unless `policy.allow_submit`.
3. **Field extraction**: label, name, type, required, options, autocomplete, surrounding text. Send to `POST /runs/{id}/plan-page`; the server returns value, source fact, confidence, sensitivity, checkpoint reasons. The adapter does not decide values.
4. **Widgets**: handle custom selects, comboboxes, date pickers, file uploads, and rich text per ATS. Employer forms may use React widgets; that is fine, they are the target, not our stack.
5. **Checkpoint triggers**: login wall, CAPTCHA/challenge, AI-restriction notice, sensitive field, unknown required, final review, blocked. Pause and wait for a recorded human decision.
6. **Fixtures**: saved HTML of each step (scrubbed) under `apps/runner/tests/fixtures/<ats>/`; tests run the extractor and filler against them offline.
7. **Logging**: each action to `run_steps` with field class, not sensitive values; screenshot key per step.
8. **Never**: stealth, solver, or proxy tooling (`job-site-access.mdc`).
