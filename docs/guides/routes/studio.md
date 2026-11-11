# `/studio`

**Status:** Documented (Phase 8)

## Behavior

Resume Studio for the active workspace. Pick a search, create a base resume from the Career Profile, run Critique / Improve / Insights, accept or reject diffs, render PDF/DOCX/text (parse gate), and inspect Skim and Parse views. The header has a short lede and each tab has a one-line explanation. **New resume** is quiet; the empty state has the single primary **Create a resume** action. Search, template, and page controls use the shared select primitive.

## Save paths

| UI | API | DB |
| --- | --- | --- |
| New base | `POST /api/v1/resumes` | `resume_versions` |
| Critique | `POST /api/v1/resumes/{id}/critique` | `resume_versions.critique` |
| Improve | `POST /api/v1/resumes/{id}/improve` | `resume_changes` (proposed) |
| Accept / Reject | `POST /api/v1/resume-changes/{id}` or bulk | `resume_changes.status` |
| Apply accepted | `POST /api/v1/resumes/{id}/apply` | `resume_versions.content` |
| Render | `POST /api/v1/resumes/{id}/render` | `parse_gate`, R2 keys |
| Insights | `POST/GET /api/v1/tracks/{id}/insights` | `market_insights` |

## Validation

Improve/apply reject fabricated claims (`fabrication_detected`). Render without `broken` fails closed on parse gate (`parse_gate_failed`).

## RBAC

`data.read` for list/get/parse/insights get; `data.write` for create, critique, improve, decisions, render, insights refresh.

## Agent parity

Same HTTP surface for MCP later. No MCP tools in Phase 8.

## Edge cases

No Track selected: list all workspace resumes; Insights disabled. Sample &lt; 30 → low-confidence banner. Ask-metric proposals do not invent numbers.
