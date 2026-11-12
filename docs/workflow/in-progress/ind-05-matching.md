# IND-5: Matching (scratchpad)

**Branch:** `ind/01-pack-foundation` · **Started:** 2026-11-13 · **Plan:** §8

## Shipped

- Pack weights are the default blend; learned Track weights override them.
- Title equivalence groups and pack-specific generic words.
- New components: credentials (posting credential vs profile certification), shift overlap, commute distance when coordinates exist.
- Facet hard filters only fail when the posting has a known conflicting value; unknown stays eligible (P4).
- Facet boosts from `FacetDef.match.boost`.
- Credential extraction from the pack's aliases; credential verdicts in the qualifications ledger.
- Synthetic ledger rows for credentials, shifts, and pay includes; Jobs fit panel maps them to pack labels.
- Tests: hospitality components, pastry vs sous chef title protection, facet filter neutrality, weights, plus existing tech matching tests.

## Not done

- `job_fit` prompt v2 and LLM credential/shift guidance (needs an eval case and a live model).
- Physical-requirement questions remain `unknown_required` at apply time; never auto-answered.

## Verification

- `tests/test_industries_matching.py` covers pack weights, title groups, credentials, shifts, facet filter neutrality.
- Existing tech matching/ranking tests unchanged.
- `pnpm run ci:quality` passed.
