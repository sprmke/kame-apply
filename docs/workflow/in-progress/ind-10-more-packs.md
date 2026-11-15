# IND-10: More packs (scratchpad)

**Branch:** `ind/01-pack-foundation` · **Started:** 2026-11-13 · **Plan:** §5.4

## Shipped

- Ten content packs: Healthcare, Engineering, Skilled trades, Customer service and retail, Education, Logistics and driving, Finance and accounting, Admin and virtual assistance, Sales and marketing, Creative and design.
- Each has role families, detection keywords, credentials where relevant, matching weights, profile found/interview content, resume section order, AI brief, and source plan.
- Template industries map to the curated packs for healthcare, engineering, trades, education, finance, sales, and marketing.
- i18n labels for every pack family and credential; registry/i18n tests cover all packs.

## Limits

- Each pack is a useful first version; facets (specialty, unit, sector, license class) and richer templates are follow-ups.
- No pack-specific ranking eval yet beyond the shared matching tests.

## Verification

- `pnpm run ci:quality` passed (591 API tests, 3 skipped; web 18; extension 9; ui 21; evals-lite 103).
- `tests/test_industries_remaining.py` covers detection, search plan, custom pack draft/accept, advice, gaps, interview, safety fees, resume order, and prompt briefs.
- Registry/i18n tests cover every extra pack label, family, and credential.
