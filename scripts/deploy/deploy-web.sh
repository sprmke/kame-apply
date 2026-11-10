#!/usr/bin/env bash
# deploy:web:dev|prod — Nuxt generate + Cloudflare Pages publish.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=./prod-unlock.sh
source "$ROOT/scripts/deploy/prod-unlock.sh"

ENV_NAME="${1:-}"
if [[ -z "$ENV_NAME" ]]; then
  echo "Usage: deploy-web.sh <dev|prod>" >&2
  exit 2
fi
if [[ "$ENV_NAME" == "prod" ]]; then
  require_prod_unlock "deploy:web:prod"
fi

: "${NUXT_PUBLIC_API_BASE:?Set NUXT_PUBLIC_API_BASE to the deployed API URL (e.g. https://api.dev.example.com)}"

cd "$ROOT"
pnpm --filter @kame/web run generate
OUT="$ROOT/apps/web/.output/public"
if [[ ! -d "$OUT" ]]; then
  # Nuxt 4 SPA may emit to .output/public or dist
  OUT="$ROOT/apps/web/dist"
fi
if command -v wrangler >/dev/null 2>&1 && [[ -n "${CF_PAGES_PROJECT:-}" ]]; then
  wrangler pages deploy "$OUT" --project-name "$CF_PAGES_PROJECT"
else
  echo "Built static site at $OUT"
  echo "Set CF_PAGES_PROJECT and install wrangler to publish, or upload this folder in the Cloudflare dashboard."
fi
echo "OK deploy-web $ENV_NAME"
