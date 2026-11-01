# Kame Apply: documentation index

**Status:** Eng phases 0–20 complete; operator leftovers in [`phases/REMAINING.md`](./phases/REMAINING.md).
**Last updated:** 2026-11-02

Kame Apply is a multi-tenant web app that helps people find real, relevant jobs anywhere in the world, strengthen their resume using live market data, and apply faster with AI, while the human stays in control of anything that matters (logins, CAPTCHAs, sensitive data, and by default the final Submit).

## Reading order

| # | Document | What it answers |
| --- | --- | --- |
| 1 | [`prd.md`](./prd.md) | What we are building, for whom, every feature, guardrails, non-goals. **Authoritative product scope.** |
| 2 | [`research/01-landscape-existing-products.md`](./research/01-landscape-existing-products.md) | What already exists (commercial + open source), what we borrow, what we avoid. |
| 3 | [`research/02-job-discovery-and-site-access.md`](./research/02-job-discovery-and-site-access.md) | Where jobs come from, how we get global coverage, and the answer to "how do we bypass bot checks" (we don't; here is what works better). |
| 4 | [`tech-stack.md`](./tech-stack.md) | Language and framework choice with reasoning, free hosting plan. **Authoritative stack.** |
| 5 | [`architecture/overview.md`](./architecture/overview.md) | Services, data flow, multi-tenancy, data model, durable workflows. |
| 6 | [`research/03-apply-engine-and-live-view.md`](./research/03-apply-engine-and-live-view.md) | How forms get filled (extension, cloud runner, agent fallback), pause/resume, live preview + takeover. |
| 7 | [`research/04-trust-safety-and-scam-detection.md`](./research/04-trust-safety-and-scam-detection.md) | Scam/phishing scoring, PII guard, prompt-injection defense, AI-answer policy. |
| 8 | [`research/05-resume-intelligence.md`](./research/05-resume-intelligence.md) | Parsing, critique rubric, market skill research, tailoring, rendering. |
| 8b | [`research/07-how-recruiters-find-and-screen.md`](./research/07-how-recruiters-find-and-screen.md) | How recruiters and their AI (Workday HiredScore, Greenhouse, LinkedIn Recruiter) find and screen candidates, and how every Kame output is built to pass both AI and human review. |
| 8c | [`research/08-bring-your-own-claude.md`](./research/08-bring-your-own-claude.md) | Using your own Claude Code / Claude subscription on Kame Apply data (MCP server, plugin, agent inbox, Claude in Chrome) within Anthropic's terms. |
| 9a | [`design/design-system.md`](./design/design-system.md) | The new "Field Notes" visual identity (color, type, icons, signature components, layouts, motion), deliberately distinct from other Kame apps. |
| 9 | [`design/ux-blueprint.md`](./design/ux-blueprint.md) | Information architecture, screens, key flows, the criteria-builder decision, responsive rules. |
| 10 | [`research/06-agentic-workflow.md`](./research/06-agentic-workflow.md) | How we build it with AI agents: what we port from kame-desk / kame-homes / kame-hunt, external skills to install. |
| 11 | [`phases/README.md`](./phases/README.md) | **The build plan.** Ordered phases, one at a time, each with exit criteria. |
| 12 | [`review/requirements-traceability.md`](./review/requirements-traceability.md) | Every request from the original brief mapped to a feature, doc, and phase, so nothing gets missed. |
| 13 | [`review/plan-critique-and-risks.md`](./review/plan-critique-and-risks.md) | Critical review of the whole plan: failure modes, edge cases, risks, and how each is handled. |

## How to use these docs in a session

- Start any build session with `docs/phases/README.md`, then open only the current phase file plus the docs it links.
- Build one phase at a time, in order. Don't start phase N+1 until phase N's exit criteria are checked off.
- If scope changes during implementation, update `prd.md` and the phase file in the same change. These are living documents.
