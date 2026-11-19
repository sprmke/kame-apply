# IND-3: Hospitality content (scratchpad)

**Branch:** `ind/01-pack-foundation` (shared worktree) · **Started:** 2026-11-13 · **Plan:** `docs/workflow/done/multi-industry-support.md` §5.2

## Shipped

- `industries/packs/hospitality.py`: role families, kitchen facets with synonyms, criteria defaults, rank ladder, 11 credentials, matching weights, profile/resume plans, AI brief, safety signals, features.
- 15 kitchen templates in `taxonomy/seed.py`; template industry maps to the Hospitality pack.
- i18n for pack, families, facets, options, ranks, credentials, profile labels. A registry test checks every pack label key exists in `en.json`.
- Manifest tests: kitchen groups, shifts/facets visible, remote/education hidden, GitHub off, four facets.

## Not in this slice

- Answer-bank keys and profile facets (`IND-6`).
- Matching weights actually applied (`IND-5`).
- Prompt/tailoring wiring (`IND-7`).
- Discovery sources and alerts (`IND-4`).
