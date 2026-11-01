# Resume Studio + per-job tailoring

Phases 8–9. Module: `apps/api/app/resumes/` (+ `apps/api/app/applications/`). UI: `/studio`, `/tailor/:trackJobId`. Research: [`research/05`](../research/05-resume-intelligence.md), [`research/07`](../research/07-how-recruiters-find-and-screen.md).

## Model

`ResumeContent` (JSON in `resume_versions.content`): contact, optional summary line, sections (experience / skills / education / …). Every claim line carries `evidence_refs[]` pointing at Career Profile fact ids. Unverified user edits set `unverified` and fail the verifier until linked.

Tables (all `workspace_id` + RLS):

| Table | Role |
| --- | --- |
| `resume_versions` | Base/tailored/draft versions; critique, parse_gate, lens_report, R2 keys |
| `resume_changes` | Proposed Studio improve ops (accept/reject) |
| `market_insights` | Per-track aggregated demand (unique on track + window) |
| `tailor_runs` | Per-job tailor session (lens before/after, gaps, draft ids) |
| `cover_letters` | Optional 150–250 word drafts with evidence refs |
| `applications` | Accepted tailor output (`ready` / `job_closed` / …); unique per workspace+track+job |

Blobs under `ws/<workspace_id>/resumes/<version_id>/`.

## Studio pipeline (Phase 8)

1. **Create** from profile → verify → store.
2. **Critique** deterministic rubric + top 5 fixes.
3. **Market insights** on demand (`low_confidence` when sample &lt; 30).
4. **Improve** ops through the truthfulness verifier.
5. **Render** + **parse round-trip gate**.
6. **Parse / Skim** views.

## Recruiter Lens (Phase 9)

`resumes/lens.py`: grades what an ATS would see (`parse_view` + plain text) against `job_qualifications`.

- Per-qualification verdict (`met` / `partial` / `not_evidenced` / `not_met`) with quoted evidence and location.
- Overall grade A–D (must weight 0.7, preferred 0.3); knockouts separate and cap the score when failed.
- Skim zone: top must-haves visible in summary + first role bullets.
- Authenticity: banned phrases + employer consistency; optional LinkedIn paste check.
- Report stored on `resume_versions.lens_report` and `tailor_runs`; UI labels it a simulation.

## Tailor workflow (Phase 9)

`tailor_once` (service; optional DBOS enqueue in `resumes/workflows.py`):

1. Load track job + quals (`ensure_qualifications`).
2. Lens(before) on base resume (track base or profile build).
3. Plan ops: surface evidenced must-haves in posting terminology; gaps stay gaps.
4. Apply → stuffing caps → length trim → verify.
5. Lens(after); if grade would drop, keep base and explain.
6. Optional cover letter from voice profile + real matches + posting company reason.
7. Accept → freeze `kind=tailored`, parse-gate render, create/update `applications` (`status=ready`, or `job_closed` if posting closed). Re-tailor after profile edits creates a new version; the application points at the latest accepted version.

Batch / autonomy `prepare` deferred to Phase 10.

## API

### Studio

| Method | Path | Action |
| --- | --- | --- |
| GET/POST | `/api/v1/resumes` | List / create base |
| POST | `/api/v1/resumes/{id}/critique` | Critique |
| POST | `/api/v1/resumes/{id}/improve` | Propose changes |
| POST | `/api/v1/resumes/{id}/render` | Render + parse gate |
| GET/POST | `/api/v1/tracks/{id}/insights` | Market insights |

### Tailor / applications

| Method | Path | Action |
| --- | --- | --- |
| POST | `/api/v1/track-jobs/{id}/tailor` | Start tailor run |
| GET | `/api/v1/tailor-runs/{id}` | Poll / read |
| POST | `/api/v1/tailor-runs/{id}/accept` | Accept → application |
| GET | `/api/v1/applications` | List |
| GET | `/api/v1/applications/{id}` | Read |

RBAC: `data.read` / `data.write`. Cross-tenant → 404.

## Truthfulness

Deterministic verifier rejects missing evidence, fabricated numbers, and banned AI phrases. Gaps are never inserted. Evals: `test_resume_fabrication_eval.py`, `test_tailor_eval.py`.

## Prompts

Registry: `resume_critique`, `resume_verify`, `resume_lens`, `resume_tailor_review`, `cover_letter`. R1 primary path is deterministic; LLM prompts are registered for later depth.
