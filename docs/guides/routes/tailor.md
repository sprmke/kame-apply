# `/tailor/:trackJobId`

**Status:** Documented (Phase 9)

## Behavior

Per-job tailor workbench. Starts a tailor run for the track job, shows Lens grade before → after, Fit ledger with before/after verdicts, gaps, knockouts, proposed changes, resume preview, and optional cover letter. Every proposed change has Keep / Remove; the draft is rebuilt from the base resume with only the kept changes, and the Lens grade is recomputed. Accept freezes the current draft and creates or updates an application (`ready`).

Desktop: three panes (ledger / changes / preview+letter). Mobile: tabs.

## Save paths

| UI | API | DB |
| --- | --- | --- |
| Open page | `POST /api/v1/track-jobs/{id}/tailor` | `tailor_runs`, draft `resume_versions`, optional `cover_letters` |
| Keep / Remove a change | `POST /api/v1/tailor-runs/{id}/changes/{change_id}` | `resume_changes.status`; draft `resume_versions.content` rebuilt from the base |
| Accept | `POST /api/v1/tailor-runs/{id}/accept` | `applications`; resume `kind=tailored`; parse gate + R2 |

## Validation

Accept fails closed on parse gate. Fabricated claims never enter the draft. Knockout fails stay visible; never auto-inserted as skills.

## RBAC

`data.write` to start/accept; `data.read` to fetch a run.

## Agent parity

HTTP-first for MCP later. No MCP tool in Phase 9.

## Edge cases

Job closed mid-tailor → application `job_closed`. Re-tailor reuses the application row and points at the new resume version.
