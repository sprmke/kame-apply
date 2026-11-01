#!/usr/bin/env bash
# migrate:dev|prod — Alembic upgrade against a remote URL. Prod requires unlock.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=./prod-unlock.sh
source "$ROOT/scripts/deploy/prod-unlock.sh"

ENV_NAME="${1:-}"
if [[ -z "$ENV_NAME" ]]; then
  echo "Usage: migrate-remote.sh <dev|prod>" >&2
  exit 2
fi
if [[ "$ENV_NAME" == "prod" ]]; then
  require_prod_unlock "migrate:prod"
fi
: "${MIGRATION_DATABASE_URL:?Set MIGRATION_DATABASE_URL}"

# Pre-migrate backup for prod
if [[ "$ENV_NAME" == "prod" ]]; then
  bash "$ROOT/scripts/deploy/backup-db.sh" prod
fi

cd "$ROOT/apps/api"
export MIGRATION_DATABASE_URL
uv run alembic upgrade head
echo "OK migrate $ENV_NAME"
