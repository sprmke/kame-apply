# AI providers, credentials, budget

Phase 2, slice D. Code: `apps/api/app/ai/`.

## Credentials

Users bring their own provider keys (Gemini, Groq, OpenAI, Anthropic, OpenRouter, Ollama). Keys are envelope encrypted:

- `MASTER_KEK` (env, base64 32 bytes) wraps one random data key (DEK) per workspace (`workspace_keys`).
- The DEK encrypts each key with AES-256-GCM. The workspace id is bound as associated data, so a ciphertext or wrapped DEK copied to another workspace fails to decrypt.
- The API never returns a key; it returns a 4-character `key_hint` and a `status` (`untested`, `valid`, `invalid`).
- Prod refuses to start with the public local default KEK.
- Never accept or store a user's Claude.ai credentials (`research/08`). An Anthropic API key is a normal provider key.

**Rotating the master key:** set `MASTER_KEK` to the new key and `MASTER_KEK_PREVIOUS` to the old one, run `python -m app.ops.rewrap_keks` (re-wraps every `workspace_keys.wrapped_dek`, bumps `kek_version`), then remove `MASTER_KEK_PREVIOUS`. Provider keys are not re-encrypted. The script is covered by `tests/test_activity_limits_rewrap.py`.

Ollama accepts a custom base URL. Hosted deployments refuse URLs resolving to private, loopback, or link-local addresses (SSRF); local development allows them.

## Calling models

All LLM calls go through `app.ai.service`:

- `run_text(...)` for free-form text
- `run_structured(..., output_type=Model)` for strict Pydantic drafts (retries once on validation failure, then `ai_output_invalid`)

Both share the same path:

1. Resolve the tier (`bulk`, `standard`, `premium`) to a provider and model: the workspace's `tier_models` override, else the first usable credential's provider with that provider's default model for the tier.
2. Budget guard: month spend plus a pessimistic estimate of this call must fit `monthly_budget_cents` (default 500) or the call is refused with `budget_reached` (402) before any provider traffic. Workflows treat this as a pause with a `budget` reason, not a failure.
3. Run a PydanticAI agent with **no tools**, so untrusted text in `prompt` cannot trigger actions. Callers must still delimit untrusted content.
4. Record tokens and estimated cost in `ai_usage` (append-only for the app role).

Versioned prompts live in `app/ai/prompts.py`. Resume parse uses `profile_extract.v1` via `run_structured` (see `docs/architecture/profile.md`).

**Optional AI.** Features that must keep working on a free tier call `app/ai/optional.try_structured`, which returns `None` for `ai_not_configured`, `budget_reached`, `ai_provider_error`, `ai_output_invalid`, and `ai_credential_invalid`. Callers keep their deterministic result. Used by the resume critique rubric and the cover letter drafter; the letter is verified sentence by sentence against profile evidence before it is returned.

Errors: `ai_not_configured` (409), `budget_reached` (402), `ai_credential_invalid` (409), `ai_provider_error` (502/504), `ai_output_invalid` (502). Optional fallback to other providers' `valid` credentials only when `fallback_enabled` is on.

Costs are estimates from a price table in `providers.py`; unknown models use the provider's default price. Default models change often (Google retired `gemini-2.5-flash-lite` for new keys while this was built), so workspaces can override any tier and the defaults should be re-checked each phase with `RUN_LIVE_AI=1 uv run pytest apps/api/tests/test_ai_live.py`.

Reasoning models spend output tokens thinking, so very small `max_tokens` fail. The default cap is 1024 (`AI_MAX_OUTPUT_TOKENS`), the credential test uses 512.

A rejected key marks the credential `invalid`. Inside a failing HTTP request that flag rolls back with the transaction; the test endpoint (which returns normally) and workflows (which own their transactions) persist it.

## Endpoints (workspace-scoped)

`GET /ai/providers`, `GET|POST /ai/credentials`, `DELETE /ai/credentials/{id}`, `POST /ai/credentials/{id}/test`, `GET|PATCH /ai/settings`, `GET /ai/usage`. Credentials and settings: owner and admin. Usage: every role.

## Data

`workspace_keys`, `ai_credentials`, `ai_settings`, `ai_usage` (migration 0005), all RLS-forced by workspace and hidden from the read-only role.
