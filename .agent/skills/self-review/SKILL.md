---
name: self-review
description: Pre-PR self-review checklist for Kame Apply changes (correctness, tenancy, truthfulness, safety, docs).
---

# Self-review

Before saying a task is done, review your own diff:

- [ ] **Scope**: only what the phase/task asked; no drive-by refactors.
- [ ] **Tenancy**: new tables have `workspace_id` + RLS; new queries run under `WorkspaceContext`; cross-tenant test exists.
- [ ] **RBAC**: server-side role check; UI gating is only a mirror.
- [ ] **Truthfulness (P1)**: generated content traces to Career Profile facts; gaps stay gaps.
- [ ] **Untrusted input (P6)**: postings/emails/pages reach the LLM only as delimited data; acting tools never take instructions from them.
- [ ] **PII**: no sensitive values or resume text in logs, Sentry, or prompts beyond need (`pii-guard.mdc`).
- [ ] **Site access (P2/P5)**: no evasion tooling; politeness limits and source terms respected (`job-site-access.mdc`).
- [ ] **Audit**: `activity_log` event or `activity-log: N/A — <why>`.
- [ ] **States**: loading, empty, error; mobile at 375.
- [ ] **AI**: prompt change has an eval case; output is a draft until accepted.
- [ ] **Docs**: updated in the same change (`documentation-maintenance`); phase checklist ticked.
- [ ] **Quality**: `pnpm run ci:quality` green (once it exists), tests cover the new behavior.
- [ ] No prod command run or recommended without the unlock word.
