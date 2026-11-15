# IND-6: Profile and answers (scratchpad)

**Branch:** `ind/01-pack-foundation` · **Started:** 2026-11-13 · **Plan:** §9

## Shipped

- `profile_facets` tenant table (RLS, unique per profile/key/value) with the standard section CRUD at `/profiles/{id}/facets`; audit actions.
- Profile page section for cuisine, kitchen type, station, and covers; add/remove values from the pack definitions.
- `CanonicalKey.packs` and pack add/hide rules; `GET /profiles/{id}/answers/keys` and quick setup filter by enabled packs. Hospitality keys added.
- `profile_certifications.credential_key`.
- Portfolio images: JPG/PNG/WebP for `kind=portfolio`, re-encoded to strip EXIF/GPS; "Add dish photo" on Documents.
- Tests: facet CRUD, duplicate 409, cross-tenant RLS, answer-key filtering, EXIF strip.

## Not done

- `profile_extract` prompt v2 (pack brief + facets) and pack interview gap questions. The deterministic facets UI and answer keys work without them.
- Per-pack completeness meter.

## Verification

- `tests/test_industries_profile.py` covers facet CRUD, duplicate 409, cross-tenant RLS, answer-key filtering, EXIF strip.
- Manual UI: added Filipino to profile facets; Documents shows "Add dish photo" for Hospitality.
- `pnpm run ci:quality` passed.
