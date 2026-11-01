#!/usr/bin/env bash
# backup:db:dev|prod — dump Postgres (read-only dump; allowed without unlock).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_NAME="${1:-dev}"
OUT_DIR="${2:-$ROOT/.backups}"
mkdir -p "$OUT_DIR"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
out="$OUT_DIR/kame-apply-${ENV_NAME}-${stamp}.dump"

if [[ "$ENV_NAME" == "dev" || "$ENV_NAME" == "local" ]]; then
  url="${MIGRATION_DATABASE_URL:-postgresql://kame_apply:kame_apply_local_only@127.0.0.1:5442/kame_apply}"
else
  : "${MIGRATION_DATABASE_URL:?Set MIGRATION_DATABASE_URL for prod backups}"
  url="$MIGRATION_DATABASE_URL"
fi
# Strip SQLAlchemy dialect suffix if present
url="${url/postgresql+asyncpg/postgresql}"
echo "Writing $out"
pg_dump --format=custom --no-owner --file="$out" "$url"
echo "OK $out"
