# Setup from a resume

One resume upload fills the pages about a person: profile facts, answer bank, writing style, searches with criteria and automation, a base resume in Studio, and a gap plan. The user checks everything on one review screen; nothing is written until they apply it.

Plan: [`docs/workflow/in-progress/setup-from-resume.md`](../workflow/in-progress/setup-from-resume.md). Product scope: [`prd.md`](../prd.md) F1.

## 1. Shape

```text
POST /onboarding/setups ─► setup_drafts row (queued) ─► background pipeline
                                                            │ steps checkpointed in `steps`
GET /onboarding/setups/{id} (poll) ◄────────────────────────┘ bundle ready
Review screen ─► PATCH decisions (autosave) ─► validate ─► apply (one transaction)
```

- The draft lives on the server, not the browser, so reloads, a second device, retry with AI, and undo all work.
- Apply calls the existing profile, answer, track, schedule, voice, resume, and account services. Setup adds no second write path.
- AI output is a draft until the user accepts it (invariant 3).

## 2. Table: `setup_drafts`

Migration `0042` (see [`deployment.md`](./deployment.md)). Workspace-scoped with a forced RLS policy, like every tenant table.

| Column | Type | Notes |
| --- | --- | --- |
| `id` | uuid pk | |
| `workspace_id` | uuid not null | RLS, on delete cascade |
| `profile_id` | uuid not null | `candidate_profiles`, on delete cascade |
| `document_id` | uuid null | `documents`, on delete set null |
| `created_by` | uuid null | `users`, on delete set null |
| `subject` | varchar(16) | `self` or `other_person` |
| `mode` | varchar(16) | `new` (empty profile) or `update` (merge rules) |
| `status` | varchar(16) | `queued`, `running`, `ready`, `applying`, `applied`, `failed`, `cancelled`, `discarded`, `expired`, `reverted` |
| `role_text` | text | Optional "what next" sentence |
| `inputs` | jsonb | Device timezone, locale, options. No resume text |
| `steps` | jsonb | Per step: status, source (`ai`/`rules`/`skipped`), reason, timings, prompt version |
| `bundle` | jsonb null | `SetupBundle` v1 |
| `decisions` | jsonb | Per item: action, edited value; plus seen pages |
| `base` | jsonb | Snapshot for stale detection |
| `result` | jsonb null | Created and updated ids, before-values for revert |
| `apply_key` | varchar(64) null | Idempotency key of the successful apply |
| `error_code` | varchar(64) null | Plain reason code |
| `ai_cost_micros` | bigint | Sum for this draft (also in `ai_usage`) |
| `expires_at` | timestamptz | 14 days after creation while open |
| `applied_at`, `created_at`, `updated_at` | timestamptz | UTC |

Constraints and indexes:

- Partial unique index `uq_setup_drafts_open_profile` on `profile_id` where the status is open (`queued`, `running`, `ready`, `applying`): one open draft per profile.
- `ix_setup_drafts_workspace_created` on `(workspace_id, created_at desc)`.
- Check constraints on `status`, `subject`, `mode`, and a non-negative `ai_cost_micros`.

Retention (scheduler loop):

| Job | When | Effect |
| --- | --- | --- |
| `expire_setups` | Every tick | Open drafts past `expires_at` become `expired` |
| `clear_setup_content` | Daily at 03:00 UTC | Finished drafts older than 30 days lose `bundle`, `decisions`, `result`, and the values carried in `steps` (signals, searches, country); step statuses and the metadata row stay |

## 3. Bundle contract

`SetupBundle` (all models `extra="forbid"`):

| Field | Limit | Meaning |
| --- | --- | --- |
| `schema_version` | `1` | Bump when the item shape changes |
| `items` | 600 | Every proposed value, grouped by page |
| `searches` | 3 | `SearchProposal` with validated `CriteriaV1` and schedule defaults |
| `profile_merge` | null | Update mode: existing merge preview |
| `notices` | 20 | i18n keys such as `ai_off_basics_only` |
| `counts` | per group | Summary sentence |

`SetupItem`: stable `id` (max 200), `group` (`profile`, `answers`, `writing`, `searches`, `studio`, `account`, `industry`), `target`, `kind`, `value`, `current`, `action` (`add`, `fill_blank`, `replace`, `keep_current`, `skip`), `source` (`resume`, `you_said`, `suggested`, `default`), `confidence`, `evidence` (quote ≤ 200 chars, optional offsets), `reason_key`, `reason_params`, `needs_you`, `blocked`, `default_on`.

Rules enforced by the contract:

- A `needs_you` item cannot carry a value. It is a question, not a guess.
- Item ids are unique inside a bundle.
- At most 600 item decisions, each a known action.

Targets are typed in [`apps/api/app/onboarding/targets.py`](../../apps/api/app/onboarding/targets.py). Each target re-validates against the same schema its service uses (`ProfileUpdate`, `ExperienceIn`, `AnswerCreate` rules, `CriteriaV1`, `VoicePresetBody`, `MeUpdate`, and so on). Unknown targets and invalid values fail the draft before the review screen, never during the write.

## 4. Pipeline

| # | Step | AI | Writes | On failure |
| --- | --- | --- | --- | --- |
| 1 | `read_file` | No | — | `needs_ocr` or `setup_document_unreadable` fails the draft with a plain reason |
| 2 | `check_document` | No | `steps` only | Not resume-like becomes a notice plus the review screen; language detected; sensitive lines counted by kind |
| 3 | `extract_profile` | Yes (`profile_extract.v1`) | `documents.parsed`, `parse_quality` | No key, no budget, timeout, or provider error falls back to rules with a notice |
| 4 | `stated_signals` | Rules + AI (S3) | `steps` | Rules only |
| 5 | `normalize` | No | `steps` | Country or taxonomy miss leaves the value empty; never guessed |
| 6 | `plan_searches` | AI (S3) | `steps` | Deterministic plan |
| 7 | `draft_rest` | Optional AI (S3) | `steps` | Skipped |
| 8 | `ground_and_build` | No | `bundle`, status `ready` | `setup_build_failed`; never a half bundle |

- Steps write to `steps` before the next starts, so `retry` resumes at the first unfinished step.
- Each AI step has a 60 s timeout; a timeout falls back to rules instead of failing the draft.
- Up-front budget check: if the workspace cannot cover a 15 cent estimate, AI steps are skipped and the bundle says so.
- Background mode commits one step per transaction and a reaper fails drafts with no progress for 3 minutes (`setup_interrupted`); **Try again** resumes. Durability comes from the checkpoints, not from DBOS.
- Tests and local non-dev runs execute the same steps inline in the request transaction.

## 5. API

| Call | Access | Purpose |
| --- | --- | --- |
| `POST /onboarding/setups` | `data.write` | Start from an uploaded `document_id` or pasted `text` (min 200 chars), plus optional `role_text`, `timezone`, `subject`, `profile_id`, `with_ai`. `202` + `SetupRead` |
| `GET /onboarding/setups` | `data.read` | The open draft for a profile (query `profile_id`, else the default profile) |
| `GET /onboarding/setups/{id}` | `data.read` | Status, steps, bundle, decisions |
| `POST .../{id}/cancel` | `data.write` | Stop a queued or running draft |
| `POST .../{id}/retry` | `data.write` | Resume a failed draft, or `{"with_ai": true}` to upgrade a rules draft |
| `POST .../{id}/discard` | `data.write` | Close a ready, failed, or cancelled draft |
| `PATCH .../{id}/decisions` | `data.write` | Review autosave; validates item ids and edited values |
| `POST .../{id}/validate` | `data.write` | Dry run: per-item errors, nothing written |
| `POST .../{id}/apply` | `data.write` | `Idempotency-Key` header required. One transaction, then after-commit jobs |
| `POST .../{id}/revert` | `data.write` | Undo within 7 days, only untouched rows |
| `POST .../{id}/seen` | `data.write` | Hide the marker on one page |
| `GET .../provenance?profile_id=` | `data.read` | Latest applied draft: ids per kind and `applied_at` |

A file upload reuses `POST /profiles/{id}/documents` (type sniffing, 10 MB cap, local text extraction); the draft then takes that `document_id`. `POST /onboarding/plan` stays for one release for older clients.

Error codes: `setup_open_exists` (409, with the open draft id), `setup_not_found` (404), `setup_document_unreadable` (422), `setup_not_running` (409), `setup_not_retryable` (409), `setup_not_discardable` (409), `setup_limit_reached` (429, 10 drafts a workspace a day).

## 6. Apply

1. **Lock** the draft row (`FOR UPDATE`).
2. **Idempotency**: applied with the same `Idempotency-Key` returns the stored result; a different key is `409 setup_already_applied`; `applying` is `409 setup_apply_in_progress`.
3. **Stale check** compares the `base` snapshot (profile `updated_at`, active search ids, touched answers) and returns `409 setup_stale` with item ids. Only those rows refresh in the UI.
4. **Validate** every selected value through its target and the owning service schema. Any error returns `422 setup_invalid_items` with per-item messages; nothing is written.
5. **One transaction**, in this order: profile header, profile facts, answers, writing preset, lowest pay, searches and schedules, Studio base resume, account name and timezone. Each call goes through the existing service and writes its own audit row.
6. **Lowest pay fans out**: one reviewed amount (currency and period included) writes the profile pay floor, the `salary_expectation` answer as approved, and the minimum on every selected search. Leaving it empty writes none of the three.
7. **Record** created and updated ids plus before-values and written values in `result`, then set `applied`, `applied_at`, and `apply_key`. Setup adds one `setup.applied` row with counts only.
8. **After commit**, outside the transaction: refresh the gap plan for each new search. The first discovery run starts in dev and prod when **Find jobs now** is on. A Needs you entry ("N answers only you can give") points to Answers for 30 days.

**Search edits**: the review can send a full `SearchProposal` per variant in `decisions.searches`. Apply re-validates it as criteria, keeps only the person's own skills as must-haves, and forces languages, education, and clearance back to empty. It never invents a title exclusion.

**Update mode**: the pipeline annotates every item with its current value and defaults to `keep_current` or `blocked=duplicate`. An approved answer is never replaced by default. A suggested search that shares 70 percent of its titles with an active search is marked duplicate and off. When the workspace search cap is reached, extra proposals are `blocked=limit`. The full merge-preview sheet from `profiles/merge.py` is not wired yet; update mode never overwrites, it only proposes additions to blanks.

**Revert** (7 days): deletes searches with no applications (archives the rest), deletes answers and facts that still equal what setup wrote, deletes an unchanged base resume, and restores header fields, the writing preset, and the account name where the current value still equals the written one. The response lists what it kept and why. `setup.reverted` records counts.

**Permissions**: `viewer` cannot start, review, apply, or revert. Account items only ever touch the caller's own user row.

## 7. Security and privacy

- Every query runs through `WorkspaceContext`; the table has forced RLS. Cross-tenant ids return 404 at the route layer and zero rows at the database layer.
- The bundle holds the same class of personal data as `documents.parsed`. It is never logged, never sent to Sentry, and never included in error payloads. Logs carry ids, step names, and reason codes only.
- Resume text is untrusted data (P6): sanitized before extraction, delimited, and read by tool-less model calls.
- Sensitive classes (date of birth, age, gender, marital status, nationality, religion, photo, height and weight, government IDs, full street address) are never read or stored.
- Export includes `setup_drafts` (metadata plus the bundle while it exists); workspace purge removes rows by cascade.

## 8. Markers and needs-you

`GET .../provenance` returns ids per kind, `applied_at`, and `seen_pages` for the latest applied draft. Pages show one line, "Filled from your resume", with the page's own AI control; **Got it** records the page in `decisions.seen_pages`, and the line disappears 14 days after apply. Today shows **Setup done** for 7 days with **Undo setup**, and **Finish checking your setup** while a draft is open. Answers left empty become the Needs you entry.

## 9. What is not filled

Jobs, Applications, Tailor, Replies, Safety, Contacts, AI keys, Connections, Alerts, Notifications, Members, Sessions, Activity, Admin, and the Danger zone have no resume-driven values. Jobs and applications fill from the first search run that setup starts.

## 10. Agent parity

Starting and applying a setup stay in the web UI: it is a one-time review that needs a file upload. The agent bridge exposes a read-only `get_setup_draft` tool (status, counts, needs-you item ids, search names, no resume text, values, or quotes). It needs `profile:read`.
