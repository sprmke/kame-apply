# Trust & safety (Phase 7)

Explainable job risk, untrusted-content sanitization, PII field classes, and Check-this.

## Risk funnel (L1–L7)

| Layer | Module | Notes |
| --- | --- | --- |
| L1 Content rules | `safety/rules.yaml` + `rules_engine.py` | Fees, chat-only, crypto, ID asks, injection |
| L2 Source trust | `source_trust.py` | Greenhouse/Lever/… hosts; verified ATS starts greener |
| L3 Domain/email | `domain_intel.py` | RDAP age, DNS, lookalike; soft-fail → `partial` |
| L4 Links | `links.py` | Redirect resolve (no JS), shorteners, Safe Browsing / URLhaus when keyed |
| L5 ML | `ml_classifier.py` | TF-IDF + LR (`artifacts/emscad_tfidf_lr.joblib`); train via `scripts/train_emscad_classifier.py` |
| L6 LLM | `assess.py` | Uncertain band only; stub until AI wired |
| L7 Community | `risk_overrides` reports | Capped; never alone enough for red on verified ATS |

Aggregator (`aggregate.py`) → `job_risk` (global). Per-workspace decisions in `risk_overrides` (`continue` / `skip` / `reported` / `not_scam`). Red `continue` requires `confirm_risk`.

Calibration: missing salary alone never red; new domain alone caps at yellow. Targets: false-red on legit ATS < 3%; scam red recall ≥ 85% (`tests/evals/test_risk_eval.py`).

## Sanitize (PRD P6)

`safety/sanitize.py`: strip hidden HTML, comments, zero-width, scripts; drop injection lines; `for_ai_context` delimits data. Profiles re-export the same helpers. Injection corpus: `tests/evals/test_injection_eval.py` (≥50 → 0 leaks).

Env: `SAFETY_SKIP_NETWORK=1` (tests), `GOOGLE_SAFE_BROWSING_API_KEY`, `GITHUB_TOKEN` (Check-this repo metadata).

## PII

`safety/pii.py`: `public` / `personal` / `sensitive`. Unknown → sensitive + checkpoint. Eval: `tests/evals/test_pii_eval.py`.

## Check-this

`POST /api/v1/safety/check-this` with `text` or `url`. GitHub metadata only (lifecycle scripts, stars, age). Never clones or executes.

## API

| Method | Path |
| --- | --- |
| GET | `/api/v1/safety/flagged` |
| GET | `/api/v1/jobs/{id}/risk` |
| POST | `/api/v1/jobs/{id}/risk/assess` |
| POST | `/api/v1/jobs/{id}/risk/decision` |
| POST | `/api/v1/safety/mid-run` |
| POST | `/api/v1/safety/check-this` |
| POST | `/api/v1/safety/classify-field` |

Discovery/scoring calls cheap `assess_and_store` (no network). DBOS enqueue: `safety/workflows.py` when `DBOS_SYSTEM_DATABASE_URL` is set.

Mid-run (`POST /safety/mid-run`): job must be linked via `track_jobs` in the workspace; signal names allowlisted; weight capped (25 each, 40 total) so clients cannot force global red.

## UI

`/safety`: Flagged list + Check this. Jobs board: `FnRiskSeal` + reason quotes; Continue confirms red risk.
