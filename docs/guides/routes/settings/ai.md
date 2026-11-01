# Route: `/settings/ai`

**Page:** `apps/web/app/pages/settings/ai.vue` · **Layout:** `default` · **Access:** signed in; keys and budget need owner or admin, usage is visible to all

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Add and test a key | acceptance.spec.ts (live Gemini) | provider, key required except Ollama | Done | Saves, then runs a small test call |
| Budget | acceptance.spec.ts | USD, capped by workspace limit | Done |  |
| Usage meter and chart | acceptance.spec.ts | n/a | Done | Chart has a table view |
| Tiers and fallback | pytest `test_ai.py` | provider known, model text | Done |  |

## Overview

Bring your own AI provider key, set a monthly budget, and see spend.

## User-facing knowledge

Add a key for Gemini, Groq, OpenAI, Anthropic, OpenRouter or Ollama. We encrypt it and show only its last four characters. Calls stop when the month's estimated spend would pass your budget.

**Common user questions**

- **Where is my key stored?** Encrypted at rest with a per-workspace key. It is never shown again.
- **What does Test do?** Makes one tiny call to confirm the provider accepts the key.
- **What happens at the budget?** AI features pause with an 'AI budget reached' message until you raise it or the month rolls over.
- **Which model runs what?** Bulk, Standard and Premium tiers map to a provider and model. Auto uses your first working key; change it under Models by tier.

## Usage

Spend this month against the budget with a daily chart and a table view.

## Provider keys

Table with masked key, status, Test and Delete.

## Monthly budget

Amount in USD.

## Models by tier

Provider and model per tier, plus fallback to another provider if a key is rejected.

## API reference

| Call | Purpose |
| --- | --- |
| `GET|POST /api/v1/ai/credentials`, `DELETE`, `POST .../{id}/test` | Keys |
| `GET|PATCH /api/v1/ai/settings` | Budget, tiers, fallback |
| `GET /api/v1/ai/usage` | Meter and chart |
| `GET /api/v1/ai/providers` | Provider list and default models |

## Implementation map

`pages/settings/ai.vue`, `components/UsageMeter.vue`, `components/UsageChart.vue`; i18n `ai.*`, `usage.*`. Details: `docs/architecture/ai-providers.md`.
