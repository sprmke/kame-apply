#!/usr/bin/env bash
# Restore a custom-format dump. Prod requires APPLYWAVE=applywave.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=./prod-unlock.sh
source "$ROOT/scripts/deploy/prod-unlock.sh"

ENV_NAME="${1:-}"
DUMP="${2:-}"
if [[ -z "$ENV_NAME" || -z "$DUMP" || ! -f "$DUMP" ]]; then
  echo "Usage: restore-db.sh <local|dev|prod> <dump-file>" >&2
  exit 2
fi
if [[ "$ENV_NAME" == "prod" ]]; then
  require_prod_unlock "rollback:db:prod restore $DUMP"
fi

if [[ "$ENV_NAME" == "local" || "$ENV_NAME" == "dev" ]]; then
  url="${MIGRATION_DATABASE_URL:-postgresql://kame_apply:kame_apply_local_only@127.0.0.1:5442/kame_apply}"
else
  : "${MIGRATION_DATABASE_URL:?Set MIGRATION_DATABASE_URL}"
  url="$MIGRATION_DATABASE_URL"
fi
url="${url/postgresql+asyncpg/postgresql}"
echo "Restoring $DUMP → $ENV_NAME"
pg_restore --clean --if-exists --no-owner --dbname="$url" "$DUMP"
echo "OK restore"
