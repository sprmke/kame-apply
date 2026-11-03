# Kame Apply: build plan (phases)

The execution plan from an empty repo to Release 1 (MVP) and Release 2. Scope is defined in [`../prd.md`](../prd.md), stack in [`../tech-stack.md`](../tech-stack.md), architecture in [`../architecture/overview.md`](../architecture/overview.md).

## How to use this

- Work **one phase at a time, in order**. Don't start phase N+1 until phase N's exit criteria are checked off (a phase may start early only where "Depends on" allows parallel work and the user agrees).
- Each phase file is self-contained: goal, outcome scenarios, tasks per layer, data model, API, UX details, edge cases, security, testing, docs, exit criteria.
- Every phase ends with: `pnpm run ci:quality` green, acceptance scenarios verified in the running app (not just tests), screenshots at 375/820/1440 for UI phases, docs updated, status flipped below.
- If scope changes during implementation, edit the phase file and `prd.md` in the same change.
- The build loop and Definition of Done are in [`../research/06-agentic-workflow.md`](../research/06-agentic-workflow.md#3-the-build-loop-every-phase).

## Status table

| # | Phase | Release | Status | Depends on |
| --- | --- | --- | --- | --- |
| 0 | [AI tooling & agentic workflow](./phase-00-ai-tooling-and-agent-setup.md) | Foundation | Done | — |
| 1 | [Monorepo scaffold, local infra, CI, technical spikes](./phase-01-scaffold-infra-spikes.md) | Foundation | Done | 0 |
| 2 | [Auth, workspaces (multi-tenancy), RBAC, audit, AI providers, app shell & design system](./phase-02-auth-tenancy-shell.md) | R1 | Done (not merged) | 1 |
| 3 | [Career Profile: resume intake, parsing, profile interview, answer bank, voice](./phase-03-career-profile.md) | R1 | Done (not merged) | 2 |
| 4 | [Tracks & criteria builder + occupation/skills taxonomy](./phase-04-tracks-and-criteria.md) | R1 | Done (not merged) | 3 |
| 5 | [Job discovery engine v1: sources, company directory, normalization, dedupe](./phase-05-job-discovery.md) | R1 | Done (not merged) | 4 |
| 6 | [Qualification extraction, matching & ranking, job research board](./phase-06-matching-and-job-board.md) | R1 | Done (not merged) | 5 |
| 7 | [Trust & safety: scam scoring, PII guard, injection defense, Check-this](./phase-07-trust-and-safety.md) | R1 | Done (not merged) | 6 |
| 8 | [Resume Studio: critique, market insights, improved base resume, rendering + parse gate](./phase-08-resume-studio.md) | R1 | Done (not merged) | 6 |
| 9 | [Per-job tailoring, Recruiter Lens, cover letters](./phase-09-tailoring-and-recruiter-lens.md) | R1 | Done (not merged) | 8 |
| 10 | [Scheduling, automation chain, notifications](./phase-10-scheduling-and-notifications.md) | R1 | Done | 7, 9 |
| 11 | [Applications tracker & command center](./phase-11-tracker-and-command-center.md) | R1 | Done | 10 |
| 12 | [Answer Desk](./phase-12-answer-desk.md) | R1 | Done | 9 |
| 12b | [Claude Agent Bridge: MCP server, Claude Code plugin, agent inbox](./phase-12b-claude-agent-bridge.md) | R1 | Done | 12 |
| 13 | [Browser extension: clip, autofill, answer insert, log applied](./phase-13-browser-extension.md) | R1 | Done | 11, 12 |
| 14 | [Release 1 hardening, free-tier deploy, personal beta](./phase-14-r1-hardening-and-launch.md) | R1 | Eng done (dogfood/uptime need prod + applywave) | 13 |
| 15 | [Cloud apply runner (assist) with durable checkpoints](./phase-15-cloud-apply-runner.md) | R2 | Done (eng) | 14 |
| 16 | [Live view & takeover](./phase-16-live-view-and-takeover.md) | R2 | Done (eng) | 15 |
| 17 | [Email alert ingestion, web push, Telegram](./phase-17-email-ingestion-and-push.md) | R2 | Done (eng) | 14 |
| 18 | [Be Found + smart application strategy](./phase-18-be-found-and-strategy.md) | R2 | Done (eng) | 14 |
| 19 | [Auto-submit policies](./phase-19-auto-submit.md) | Later | Done (eng; live gated) | 16, real-usage data |
| 20 | [Response tracking, interview prep, coach/agency workspaces](./phase-20-later-features.md) | Later | Done (eng) | 17 |

Phases 7 and 8 both depend only on 6 and may run in either order. Phases 17 and 18 can run in parallel with 15–16.

The 2026-11-03 full review ([`../reviews/full-review-phases-0-20.md`](../reviews/full-review-phases-0-20.md)) fixed the P0 safety/tenancy/truthfulness defects and lists the gaps that are still open (LLM critique, discovery SSE, runner packaging, closed-job detection for feeds, auto-submit execution). Read it before trusting a phase's Done status for those areas.

**After eng 0–20:** only operator/human leftovers remain. See [`REMAINING.md`](./REMAINING.md).

## Why this order

1. **Tooling first** (0): every later phase is built by agents, and the guardrails (truthfulness, no evasion, tenancy) must exist before code does.
2. **Identity and tenancy before data** (2): retrofitting RLS is painful and dangerous.
3. **Profile before everything AI** (3): it's the single source of truth that makes truthful output possible.
4. **Find → rank → protect → improve → tailor** (5–9): the interview-rate drivers from research/07, in dependency order.
5. **Automate what's proven** (10–13): scheduling and the extension wrap features that already work manually.
6. **Ship and use it** (14) before building the riskiest component (cloud runner, 15–16), so real usage informs it.
7. **Auto-submit last** (19), only if data shows assist mode is the bottleneck.
