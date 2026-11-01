#!/usr/bin/env bash
# Idempotently create the restricted local roles and grants. Safe to re-run; LOCAL docker Postgres only.
# kame_apply        owner/migration role (superuser locally, as the compose image makes it)
# kame_apply_app    runtime role used by the API: NOSUPERUSER, NOBYPASSRLS (RLS applies to it)
# kame_apply_ro     read-only role for the postgres MCP server
set -euo pipefail
cd "$(dirname "$0")/../.."
PSQL=(docker compose -f infra/docker-compose.dev.yml exec -T postgres psql -U kame_apply -v ON_ERROR_STOP=1 -q)
"${PSQL[@]}" -d postgres <<'SQL'
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'kame_apply_app') THEN
    CREATE ROLE kame_apply_app LOGIN PASSWORD 'kame_apply_app_local_only'
      NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'kame_apply_ro') THEN
    CREATE ROLE kame_apply_ro LOGIN PASSWORD 'kame_apply_ro_local_only'
      NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
  END IF;
END $$;
SQL
for db in kame_apply kame_apply_test; do
  "${PSQL[@]}" -d "$db" <<SQL
GRANT CONNECT ON DATABASE $db TO kame_apply_app, kame_apply_ro;
GRANT USAGE ON SCHEMA public TO kame_apply_app, kame_apply_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE kame_apply IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO kame_apply_app;
ALTER DEFAULT PRIVILEGES FOR ROLE kame_apply IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO kame_apply_app;
ALTER DEFAULT PRIVILEGES FOR ROLE kame_apply IN SCHEMA public
  GRANT SELECT ON TABLES TO kame_apply_ro;
SQL
done
echo "OK — db roles ensured"
