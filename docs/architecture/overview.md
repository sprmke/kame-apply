# Architecture overview

**Status:** Planned · **Last updated:** 2026-10-28 · Stack decisions: [`../tech-stack.md`](../tech-stack.md)

## 1. System diagram

```
┌──────────────────────────────┐     ┌────────────────────────────────────┐
│ Web app (Cloudflare Pages)   │     │ Browser extension (WXT, MV3)       │
│ Vue 3 + Nuxt 4 (SPA)         │     │ Vue side panel · content scripts   │
│ Vue Query · Hey API client   │     │ clip job · autofill · log applied  │
└──────────────┬───────────────┘     └──────────────────┬─────────────────┘
               │ HTTPS REST /api/v1 · SSE · WSS          │ HTTPS (extension token)
               ▼                                         ▼
┌────────────────────────────────────────────────────────────────────────────────┐
│ apps/api  (FastAPI, always-on, Oracle A1 VM, Docker Compose behind Caddy)      │
│  ├─ REST routers (auth, workspaces, profiles, tracks, jobs, resumes, apps ...) │
│  ├─ SSE: AI streaming (tailoring, answers, critique)                           │
│  ├─ WS: run events + live-view relay (frames ⇄ input)                          │
│  ├─ Services (all business logic)                                              │
│  └─ DBOS workflows (in-process): discovery, scoring, safety, tailoring,        │
│     apply orchestration, schedules (cron), queues (rate-limited per host)      │
└───────────────┬───────────────────────────────┬────────────────────────────────┘
                │ SQL                            │ DBOS queue "apply_runs" + WS
                ▼                                ▼
┌──────────────────────────────┐   ┌─────────────────────────────────────────────┐
│ PostgreSQL 17                │   │ apps/runner (Playwright, separate container) │
│ app data · RLS · pgvector    │   │ hosted on the VM OR on the user's machine    │
│ pg_trgm FTS · DBOS state     │   │ ATS adapters · generic filler · browser-use  │
└──────────────────────────────┘   │ CDP screencast → API WS relay                │
                                   └─────────────────────────────────────────────┘
User-side agents (their own subscription): Claude Code / Claude Desktop / claude.ai connector / user's own `claude -p`
          ──MCP over HTTPS + OAuth──► apps/api /mcp  (tools · resources · prompts · agent inbox)
External: Cloudflare R2 (files) · Resend (email out) · CF Email Routing→Worker (alerts in)
          LLM providers (BYO key / Ollama) · job sources (ATS APIs, board APIs, career pages)
```

**Invariants**

1. FastAPI owns all business logic. Web and extension are UI only.
2. Every tenant-owned row carries `workspace_id`, and every request sets `app.workspace_id` for RLS. There is no query path without scope.
3. AI output is a **draft** until the user accepts it (resume changes, answers, cover letters, status changes from email).
4. Untrusted text (postings, emails, web pages) is sanitized and passed to the LLM only as delimited data. Tools that act (fill, submit) never take instructions from that text.
5. Every state-changing action writes an append-only `activity_log` row (who/what/when/before/after, no secrets).
6. Blobs (resumes, screenshots, snapshots) live in R2, referenced by key. Never in Postgres.
7. A run may only continue past a checkpoint after a recorded human decision.

## 2. Services and modules (`apps/api/app/`)

| Module | Responsibility |
| --- | --- |
| `auth` | Sign-up/login, Google OAuth, JWT access/refresh, sessions, extension tokens, MFA (P1). |
| `workspaces` | Tenancy, members, roles, invitations, settings, plan limits, AI keys (encrypted), budgets. |
| `profiles` | Candidate Profiles, facts (experience, education, skills, projects...), answer bank, voice profile, documents. |
| `taxonomy` | ESCO/O*NET occupations and skills, synonyms, title normalization, skill extraction/mapping. Details: [`criteria-and-taxonomy.md`](./criteria-and-taxonomy.md). |
| `tracks` | Tracks, criteria (structured + NL), compiled filters, schedules, autonomy policy, caps. Details: [`criteria-and-taxonomy.md`](./criteria-and-taxonomy.md). |
| `sources` | Source adapters (Layers 1–6), company directory, polling tiers, politeness, health. |
| `jobs` | Normalization, dedupe, expiry, qualification extraction, job snapshots. |
| `matching` | Hard filters, rule score, embeddings, LLM fit, feedback learning. Details: [`matching.md`](./matching.md). |
| `safety` | Scam/phishing scoring, PII field classifier, prompt-injection sanitizer, vetting tool. Details: [`safety.md`](./safety.md). |
| `resumes` | Critique, market insights, base resume, Recruiter Lens, per-job tailor, cover letters, rendering, parse gate. Details: [`resumes.md`](./resumes.md). |
| `answers` | Answer Desk drafting, AI-restriction detection, style enforcement. Details: [`answers.md`](./answers.md). |
| `applications` | Tracker, status machine, home/metrics, snapshots. Details: [`applications.md`](./applications.md). |
| `runs` | Apply run orchestration (DBOS), checkpoints, step log, screenshots, live-view sessions. |
| `ingest` | Inbound email alerts, extension clips. |
| `responses` | Recruiter reply classify + status proposals. Details: [`phase20-later.md`](./phase20-later.md). |
| `interview` | Per-application interview prep (truthful, cited). |
| `gaps` | Track skill gap plans. |
| `referrals` | Contacts import + outreach drafts (user sends). |
| `notifications` | In-app, email, web push, Telegram; preferences; digests. Details: [`automation.md`](./automation.md). |
| `ai` | Provider router, model tiers, prompt registry, cost metering, budget enforcement, eval hooks. |
| `audit` | `activity_log`, admin views. |
| `agent_bridge` | Remote MCP server (`/mcp`, Streamable HTTP), OAuth authorization server for MCP clients, tool/resource/prompt adapters over the services above, agent inbox (`agent_tasks` leasing), per-feature AI routing to "my Claude". Never handles Claude credentials ([`research/08`](../research/08-bring-your-own-claude.md)). |

## 3. Durable workflows (DBOS)

| Workflow | Trigger | Steps (each checkpointed) |
| --- | --- | --- |
| `discover_track` | Cron per Track schedule, or "Run now" | resolve sources → enqueue fetch per source (rate-limited queue per host) → normalize/dedupe → link to Track → `score_track_jobs` |
| `poll_board` | Directory polling tiers | conditional fetch → upsert jobs → mark closed |
| `score_track_jobs` | After discovery / criteria change | hard filters → rule score → embed → LLM fit for top N (budget-aware) → safety assess → notify strong matches |
| `assess_job_risk` | New job / user request | rules → domain/link intel → ML → LLM (if needed) → risk level + reasons |
| `tailor_application` | User clicks Tailor / autonomy `prepare` | extract qualifications → Lens (before) → draft changes → verify truthfulness → render → parse round-trip → Lens (after) → await user accept |
| `apply_run` | User clicks Apply (runner) / autonomy policy | preflight (risk, caps, docs ready) → open → detect ATS → page loop {extract fields → map → classify sensitivity → fill → checkpoint if needed (`DBOS.recv` with timeout) → next} → final review checkpoint → submit (or user submits) → confirm → record |
| `ingest_alert_email` | Inbound webhook | parse → resolve links → upsert jobs → match Tracks |
| `daily_digest` | Cron per user timezone | compile → send |
| `directory_refresh` | Monthly | Common Crawl CDX query → validate slugs → upsert boards |

Human checkpoints use DBOS messaging: the workflow `recv`s on topic `checkpoint:{id}`; the API `send`s the user's decision. Timeouts move the run to `needs_you` (it stays resumable) rather than failing.

## 4. Multi-tenancy

- **Tenant = workspace.** `users` ↔ `workspace_members(role)`. A user can belong to several workspaces (solo + a coach's). The active workspace is chosen in the UI and sent as a header; the API verifies membership on every request.
- **Isolation, defense in depth:**
  1. App layer: a FastAPI dependency resolves `WorkspaceContext`; repositories require it (port kame-desk `clinic-scoping` → `workspace-scoping` skill).
  2. DB layer: Postgres RLS on every tenant table: `USING (workspace_id = current_setting('app.workspace_id')::uuid)`, set via `SET LOCAL` per transaction; the app DB role is not table owner and has no `BYPASSRLS`.
  3. Tests: a cross-tenant test suite tries every endpoint with another workspace's ids and expects 404.
- **Global vs tenant data:** `companies`, `company_boards`, `jobs`, `job_sources`, `job_qualifications`, taxonomy are **global** (public data, shared, no PII). Everything the user creates or that reflects their opinion (`track_jobs` scores/status, notes, applications, risk overrides) is **tenant**.
- **Workspace-level settings:** AI provider keys (encrypted with per-workspace data keys under a master key from env, envelope encryption), budgets, caps, notification channels, data retention, export/delete.
- **Limits per workspace** (abuse and cost control): Tracks, sources, runs/day, AI spend, storage.

## 5. Data model (core tables)

Tenant tables carry `workspace_id`, `created_at`, `updated_at`, and `created_by` where useful. UUIDv7 primary keys.

```
users(id, email, name, password_hash?, google_sub?, timezone, locale)
workspaces(id, name, slug, kind[personal|team], settings jsonb)
workspace_members(workspace_id, user_id, role[owner|admin|member|viewer])
ai_credentials(workspace_id, provider, encrypted_key, model_prefs jsonb)
ai_usage(workspace_id, feature, provider, model, tokens_in, tokens_out, cost_usd, at)

candidate_profiles(id, workspace_id, display_name, headline, location, timezone, work_authorization jsonb, salary_prefs jsonb, links jsonb)
profile_experiences(id, profile_id, company, title, employment_type, location, start, end, is_current, description)
profile_bullets(id, experience_id|project_id, text, metrics jsonb, skills[], evidence_strength, source[parsed|interview|user])
profile_education / profile_projects / profile_certifications / profile_languages
profile_skills(profile_id, skill_id?, name, level, years, last_used, evidence_refs[])
answer_bank(id, profile_id, key, country?, question_variants[], answer, answer_json?, scope[global|track], track_id?, approved bool)
voice_profiles(profile_id, samples jsonb, style jsonb, banned_phrases[], analyzed_at?)
documents(id, workspace_id, profile_id, kind[resume_upload|portfolio|generated], r2_key, mime, parsed jsonb, parse_quality)

tracks(id, workspace_id, profile_id, name, icon, color, status, autonomy[discover|prepare|assist|auto_submit], base_resume_id, settings jsonb)
track_criteria(track_id, nl_text, structured jsonb, compiled jsonb, version)
track_sources(track_id, source_id, enabled, params jsonb)
schedules(id, workspace_id, track_id, scope[all|source], source_id?, cron, tz, quiet_hours, enabled, next_run_at)

sources(id, kind[ats|board|career_page|email|clip|personal], name, adapter, terms_note, enabled_global)
companies(id, name, domain, normalized_name, size, industry, hq_country, linkedin_url?, verified_domain bool)
company_boards(id, company_id, ats, slug, url, status, last_polled_at, poll_tier, etag)
jobs(id, company_id, title, normalized_title, occupation_codes[], seniority, employment_type, work_mode,
     locations jsonb, remote_eligibility jsonb, salary jsonb, skills[], description_html, description_text,
     language, posted_at, expires_at, status[open|closed], content_hash, simhash, apply_url, canonical_url, embedding vector)
job_sources(job_id, source_id, external_id, url, first_seen_at, last_seen_at)
job_qualifications(job_id, kind[must|preferred|knockout], text, normalized jsonb)   -- extracted once, reused everywhere
job_risk(job_id, level, score, reasons jsonb, model_version, assessed_at)          -- global signal
track_jobs(id, workspace_id, track_id, job_id, score, fit jsonb, eligibility, status[new|shortlisted|skipped|hidden|applied...], skip_reason, seen_at)
risk_overrides(workspace_id, job_id, decision[continue|skip|reported], note)

resume_versions(id, workspace_id, profile_id, track_id?, application_id?, kind[base|tailored], content jsonb, template, r2_pdf, r2_docx, lens_report jsonb, parent_id, accepted_at)
resume_changes(id, resume_version_id, path, before, after, reason, evidence_refs[], status[proposed|accepted|rejected])
market_insights(track_id, computed_at, skills jsonb, titles jsonb, salary jsonb, sample_size)

applications(id, workspace_id, track_id, job_id, status, method[extension|runner|manual|answer_desk], resume_version_id, cover_letter_id?, job_snapshot_r2, submitted_at, notes)
application_answers(application_id, question, answer, source[bank|drafted|user], ai_restricted bool, approved_by?)
application_events(application_id, type, payload, at)            -- status timeline
apply_runs(id, workspace_id, application_id, profile_id, source, ats, page_url, status[queued|running|needs_you|paused|completed|failed|cancelled], runner_id, dbos_workflow_id, policy jsonb, submit_approved, last_step_seq, control_mode[agent|human|paused], live_mode[off|screencast|screenshot], controller_user_id, user_edited_fields jsonb, live_telemetry jsonb, started_at, ended_at, failure_reason)
apply_run_steps(run_id, seq, page_url, action, field_label, value_redacted, canonical_key, source_fact_ref, pii_class, screenshot_r2, outcome)
apply_checkpoints(id, run_id, kind[login|captcha|ai_restricted|sensitive_field|unknown_required|answer_approval|risk|final_review|blocked], detail jsonb, status[open|resolved|expired], decided_by, decision, decided_at)
runner_tokens(id, workspace_id, user_id, token_hash, label, mode[cloud|local], last_seen_at, revoked_at)
form_signatures(signature_hash, ats, field_map jsonb)  -- global label→canonical cache; no values
site_sessions(workspace_id, site, encrypted_storage_state, created_at, last_used_at, revoked)

inbound_addresses(workspace_id, token, enabled, rotated_at)
inbound_messages(id, workspace_id, sender, subject, provider, r2_raw, parsed jobs[], status, confidence, jobs_created)
push_subscriptions(workspace_id, user_id, endpoint, p256dh, auth)
telegram_links(workspace_id, user_id, chat_id, link_code, code_expires_at, linked_at)
notifications(id, workspace_id, user_id, type, payload, read_at)
notification_prefs(user_id, workspace_id, channel[in_app|email|push|telegram], event, enabled)
activity_log(id, workspace_id, actor_type[user|system|ai], actor_id, entity, entity_id, action, diff jsonb, at)  -- append-only
```

## 6. Security essentials

- Secrets in env; per-workspace keys envelope-encrypted; `site_sessions` encrypted and revocable; never store third-party passwords.
- Live-view and runner WebSockets require short-lived signed tokens bound to workspace + run; the CDP endpoint is never exposed.
- Sensitive fields are redacted in `run_steps` and logs; screenshots blur sensitive fields detected by the PII classifier.
- Rate limiting per user/workspace on auth and AI endpoints; budget enforcement before every LLM call.
- Data export (`GET /api/v1/workspace/export` JSON without secrets) and team workspace delete with immediate R2 prefix purge (`ws/<id>/`); rows hard-removed after 30 days.
- Uploaded files: type/size validation, AV scan with ClamAV in the worker (free), never executed.
- Take-home/recruiter repos are never cloned or executed by the system (vetting reads metadata only).

## 7. Observability

Structured logs (no PII, no answers), Sentry for errors, per-workflow metrics (runs, durations, failures by reason), per-source health dashboard (success rate, latency, jobs/day, block signals), AI cost per feature per workspace, and an admin page for source and runner health.
