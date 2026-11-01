# `/safety`

**Status:** Documented (Phase 7)

## Behavior

Two tabs: **Flagged** (yellow/red jobs with reasons and decisions) and **Check this** (paste a recruiter message or URL/repo).

Continue on a red job asks for confirm that restates high risk. Report hides the job for this workspace and feeds the community signal. Not a scam records calibration feedback.

## Save paths

| UI | API | DB |
| --- | --- | --- |
| Continue / Skip / Report / Not a scam | `POST /api/v1/jobs/{id}/risk/decision` | `risk_overrides`; report may set `track_jobs.status=hidden` |
| Check | `POST /api/v1/safety/check-this` | none (read-only) |
| Flagged list | `GET /api/v1/safety/flagged` | reads `job_risk` + overrides |

## RBAC

`data.read` for list/check; `data.write` for decisions.

## Agent parity

Classify-field and Check-this are API-first for extension/runner later. No MCP tool in Phase 7.

## Edge cases

Network intel down → assessment still returns with `partial`. Check-this never clones repos.
