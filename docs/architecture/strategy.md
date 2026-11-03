# Be Found + application strategy (Phase 18)

## LinkedIn optimizer

`GET /api/v1/tracks/{id}/linkedin-optimize` builds headline (≤220), About, skills order, experience wording, Open-to-work checklist, and GitHub checklist from Career Profile + Track criteria only. Copy-paste; no LinkedIn automation. Optional prompts: `linkedin_optimize`, `linkedin_consistency`.

## Consistency

`POST /api/v1/strategy/consistency` with pasted LinkedIn text → issues (companies, titles, dates, skills) + score.

## Caps and freshness

Workspace prefs `PUT /api/v1/strategy/prefs` (`company_cap` default 3 / 90 days). Runner preflight adds a `policy.warnings` entry when the cap is reached or nearly reached; it does not block (PRD P4). `GET /applications/{id}/company-cap`. Job freshness: `GET /jobs/{id}/freshness` (high within 24h).

## Salary and follow-ups

`GET /applications/{id}/salary-advice` uses posting range + user floor (+ optional `job.meta.market_salary_p50`). `GET /applications/{id}/follow-up-drafts` returns day-7 and day-14 copy (user sends).
