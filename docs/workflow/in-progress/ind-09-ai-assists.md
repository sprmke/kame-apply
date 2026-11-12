# IND-9: AI assists (scratchpad)

**Branch:** `ind/01-pack-foundation` · **Started:** 2026-11-13 · **Plan:** §10

## Shipped

- Deterministic `industry_detect` over the pack keywords/cues; `POST /industries/detect`.
- `search_plan.v2` baseline: local titles from pack role families, pack defaults, source queries; `POST /tracks/plan`.
- Custom pack drafting: `POST /industries/draft` selects existing building blocks and validates against `IndustryPack`; `POST /workspace/industries/custom` accepts it with audit.
- `GET /sources/advice` returns coverage plus alert/employer suggestions without inventing URLs.
- AI prompt entries: `industry_detect.v1`, `search_plan.v2`, `industry_pack_draft.v1`, `source_advice.v1`.
- Tests for detection, plan, draft/accept, and advice.

## Limits

- AI runners are not wired to these endpoints yet; the deterministic fallbacks are the production path. No live detection or custom-pack eval.
- No optional web discovery provider.

## Verification

- `pnpm run ci:quality` passed (591 API tests, 3 skipped; web 18; extension 9; ui 21; evals-lite 103).
- `tests/test_industries_remaining.py` covers detection, search plan, custom pack draft/accept, advice, gaps, interview, safety fees, resume order, and prompt briefs.
- Registry/i18n tests cover every extra pack label, family, and credential.
