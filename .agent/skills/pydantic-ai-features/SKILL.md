---
name: pydantic-ai-features
description: "Building AI features with PydanticAI: prompt registry, structured outputs, provider router, budgets, SSE streaming, eval hooks."
---

# PydanticAI features

Rule: `.cursor/rules/pydantic-ai.mdc`. Library docs via `context7`.

1. **Define the contract first**: a Pydantic output model with strict fields and descriptions; the model-facing schema is the spec.
2. **Register the prompt** in the prompt registry (id, version, template, input model). Wrap untrusted text in data delimiters (`untrusted-content.mdc`).
3. **Call through the router** (`app/ai/router.py`): picks the tier (cheap/standard/strong) per feature, applies the workspace budget, meters tokens and cost, falls back across providers.
4. **Draft semantics**: persist output as a draft with evidence refs; acceptance is a separate user action with an `activity_log` event.
5. **Streaming**: SSE for long outputs; send final validated object last.
6. **Failure modes**: validation retry once, then a visible error state; budget exceeded ⇒ explain and offer the cheaper tier or the user's own Claude via the agent bridge.
7. **Evals**: add cases per `ai-evals` before merging a prompt change.
8. **Privacy**: minimum facts in context; no sensitive-class values; no PII in logs.
