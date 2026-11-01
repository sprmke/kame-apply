#!/usr/bin/env bash
# Drop and recreate the LOCAL dev database, then migrate. Refuses non-local URLs.
set -euo pipefail
cd "$(dirname "$0")/../.."
URL="${DATABASE_URL:-postgresql+asyncpg://kame_apply:kame_apply_local_only@127.0.0.1:5442/kame_apply}"
case "$URL" in *127.0.0.1*|*localhost*) ;; *) echo "Refusing: DATABASE_URL is not local"; exit 1 ;; esac
docker compose -f infra/docker-compose.dev.yml exec -T postgres \
  psql -U kame_apply -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS kame_apply WITH (FORCE)" -c "CREATE DATABASE kame_apply OWNER kame_apply"
docker compose -f infra/docker-compose.dev.yml exec -T postgres \
  psql -U kame_apply -d kame_apply -c "GRANT USAGE ON SCHEMA public TO kame_apply_ro" \
  -c "ALTER DEFAULT PRIVILEGES FOR ROLE kame_apply IN SCHEMA public GRANT SELECT ON TABLES TO kame_apply_ro" \
  -c "GRANT CONNECT ON DATABASE kame_apply TO kame_apply_ro"
bash scripts/dev/ensure-db-roles.sh
pnpm run db:migrate
pnpm run db:seed
