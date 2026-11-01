#!/usr/bin/env bash
# Local restore drill: dump → restore into kame_apply_restore_drill → sanity query → drop.
# Uses the compose Postgres container when pg_dump is not on the host PATH.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="$ROOT/.backups/drill"
mkdir -p "$OUT_DIR"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
dump="$OUT_DIR/drill-${stamp}.dump"
COMPOSE=(docker compose -f "$ROOT/infra/docker-compose.dev.yml")

pg() {
  if command -v pg_dump >/dev/null 2>&1 && command -v psql >/dev/null 2>&1; then
    "$@"
    return
  fi
  # Map host tools to the running postgres service.
  local bin="$1"
  shift
  case "$bin" in
    pg_dump)
      "${COMPOSE[@]}" exec -T postgres pg_dump -U kame_apply -d kame_apply "$@"
      ;;
    psql)
      # First arg after psql is usually the URL; for container we use -U/-d.
      "${COMPOSE[@]}" exec -T postgres psql -U kame_apply "$@"
      ;;
    pg_restore)
      "${COMPOSE[@]}" exec -T -i postgres pg_restore -U kame_apply "$@"
      ;;
    *)
      echo "unknown tool $bin" >&2
      exit 1
      ;;
  esac
}

echo "1/4 dump $dump"
if command -v pg_dump >/dev/null 2>&1; then
  url="${MIGRATION_DATABASE_URL:-postgresql://kame_apply:kame_apply_local_only@127.0.0.1:5442/kame_apply}"
  url="${url/postgresql+asyncpg/postgresql}"
  pg_dump --format=custom --no-owner --file="$dump" "$url"
else
  "${COMPOSE[@]}" exec -T postgres \
    pg_dump -U kame_apply -d kame_apply --format=custom --no-owner >"$dump"
fi

echo "2/4 create restore DB"
if command -v psql >/dev/null 2>&1; then
  admin_url="postgresql://kame_apply:kame_apply_local_only@127.0.0.1:5442/postgres"
  psql "$admin_url" -v ON_ERROR_STOP=1 -c "DROP DATABASE IF EXISTS kame_apply_restore_drill;"
  psql "$admin_url" -v ON_ERROR_STOP=1 -c "CREATE DATABASE kame_apply_restore_drill OWNER kame_apply;"
else
  "${COMPOSE[@]}" exec -T postgres \
    psql -U kame_apply -d postgres -v ON_ERROR_STOP=1 \
    -c "DROP DATABASE IF EXISTS kame_apply_restore_drill;"
  "${COMPOSE[@]}" exec -T postgres \
    psql -U kame_apply -d postgres -v ON_ERROR_STOP=1 \
    -c "CREATE DATABASE kame_apply_restore_drill OWNER kame_apply;"
fi

echo "3/4 restore"
if command -v pg_restore >/dev/null 2>&1; then
  pg_restore --no-owner --dbname="postgresql://kame_apply:kame_apply_local_only@127.0.0.1:5442/kame_apply_restore_drill" "$dump"
else
  "${COMPOSE[@]}" exec -T -i postgres \
    pg_restore -U kame_apply -d kame_apply_restore_drill --no-owner <"$dump"
fi

echo "4/4 sanity"
if command -v psql >/dev/null 2>&1; then
  tables=$(psql "postgresql://kame_apply:kame_apply_local_only@127.0.0.1:5442/kame_apply_restore_drill" -tAc \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")
else
  tables=$("${COMPOSE[@]}" exec -T postgres \
    psql -U kame_apply -d kame_apply_restore_drill -tAc \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")
fi
tables=$(echo "$tables" | tr -d '[:space:]')
echo "public tables: $tables"
if [[ "${tables:-0}" -lt 5 ]]; then
  echo "FAIL: expected more tables" >&2
  exit 1
fi

if command -v psql >/dev/null 2>&1; then
  psql "postgresql://kame_apply:kame_apply_local_only@127.0.0.1:5442/postgres" -v ON_ERROR_STOP=1 \
    -c "DROP DATABASE IF EXISTS kame_apply_restore_drill;"
else
  "${COMPOSE[@]}" exec -T postgres \
    psql -U kame_apply -d postgres -v ON_ERROR_STOP=1 \
    -c "DROP DATABASE IF EXISTS kame_apply_restore_drill;"
fi

echo "OK restore drill $stamp"
echo "$dump" >"$OUT_DIR/LAST_OK"
