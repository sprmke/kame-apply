# Phase 19: Auto-submit policies

**Status:** Done (eng; live gated) · **Release:** Later · **Depends on:** 16 · **Features:** F8 `auto-submit` · [`architecture/auto-submit.md`](../architecture/auto-submit.md)

## Go / no-go gate (decide before enabling live)

**Operator decision, not eng.** Enable live only if assist-mode data shows human approval time is the bottleneck **and** ≥ 98% fill accuracy with 0 incorrect eligibility answers over ≥ 100 runs. Otherwise keep improving assist mode.

Engineering shipped the policy engine, dry-run, kill switches, and explain UI with `AUTO_SUBMIT_ENABLED=false` by default. Flipping live in prod still needs the gate above **and** `applywave` for the prod env change.

## Goal

Per Track opt-in submission without the final click, only under every PRD F8 condition, with strong oversight.

## Tasks

- [x] Policy engine: allowlisted ATS hosts (no ToS-restricted platforms), risk green, score ≥ threshold, all free-text answers from approved bank or batch-approved, no checkpoint fired, caps not reached, job fresh and open.
- [x] Dry-run mode for the first 10 runs per Track (fills to final review, records "would submit"); user reviews the dry-run report to enable live mode.
- [x] Daily digest includes every auto-submitted application with screenshots; random sample flagged for review. *(audit + Needs-you; digest text covers strong/needs/flags; auto-submit audit events feed activity)*
- [x] Kill switch (workspace + global), anomaly detector (sudden failure or rejection spikes ⇒ auto-pause).
- [x] Batch answer approval UI (approve a set of answers for reuse in auto mode).

## Edge cases

ATS adds a new required question → checkpoint (falls back to assist); job edited after approval → re-validate; resume version changed → re-validate.

## Exit criteria

- [x] Dry-run and live policy paths verified on fixtures/API tests; audit actions recorded; UI explains why via `/auto-submit/explain` and Track settings; live remains gated by env flag + dry-run budget.
