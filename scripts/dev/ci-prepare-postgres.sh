#!/usr/bin/env bash
# Prepare Postgres for CI (service container has no compose init). Creates app/ro roles + grants.
# Expects owner: kame_apply / kame_apply_local_only @ 127.0.0.1:5442 (override via PG*).
set -euo pipefail
HOST="${PGHOST:-127.0.0.1}"
PORT="${PGPORT:-5442}"
USER="${PGUSER:-kame_apply}"
PASSWORD="${PGPASSWORD:-kame_apply_local_only}"
export PGPASSWORD="$PASSWORD"
PSQL=(psql -h "$HOST" -p "$PORT" -U "$USER" -v ON_ERROR_STOP=1 -q)

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

if ! "${PSQL[@]}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = 'kame_apply_test'" | grep -q 1; then
  "${PSQL[@]}" -d postgres -c "CREATE DATABASE kame_apply_test OWNER kame_apply"
fi

"${PSQL[@]}" -d postgres -c "GRANT CONNECT ON DATABASE kame_apply_test TO kame_apply_app, kame_apply_ro"
"${PSQL[@]}" -d kame_apply_test <<'SQL'
GRANT USAGE ON SCHEMA public TO kame_apply_app, kame_apply_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE kame_apply IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO kame_apply_app;
ALTER DEFAULT PRIVILEGES FOR ROLE kame_apply IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO kame_apply_app;
ALTER DEFAULT PRIVILEGES FOR ROLE kame_apply IN SCHEMA public
  GRANT SELECT ON TABLES TO kame_apply_ro;
SQL

echo "OK — CI Postgres roles ready"
