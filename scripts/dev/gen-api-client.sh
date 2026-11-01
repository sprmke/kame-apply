#!/usr/bin/env bash
# Regenerate packages/api-client from the FastAPI OpenAPI schema.
# --check: regenerate into place, then fail if anything differs from what was there before
# (CI drift check; independent of git state).
set -euo pipefail
cd "$(dirname "$0")/../.."
CLIENT=packages/api-client
SNAP=""
if [[ "${1:-}" == "--check" ]]; then
  SNAP="$(mktemp -d)"; trap 'rm -rf "$SNAP"' EXIT
  cp "$CLIENT/openapi.json" "$SNAP/openapi.json" 2>/dev/null || true
  [[ -d "$CLIENT/src/generated" ]] && cp -R "$CLIENT/src/generated" "$SNAP/generated"
fi
(cd apps/api && uv run python -m app.export_openapi > ../../$CLIENT/openapi.json)
pnpm --filter @kame/api-client run generate >/dev/null
if [[ -n "$SNAP" ]]; then
  if ! diff -rq "$SNAP/generated" "$CLIENT/src/generated" >/dev/null 2>&1 || ! diff -q "$SNAP/openapi.json" "$CLIENT/openapi.json" >/dev/null 2>&1; then
    echo "API client is out of date. Run: pnpm run gen:api-client and commit the result."
    exit 1
  fi
  echo "OK — API client up to date"
fi
