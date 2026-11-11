#!/usr/bin/env bash
# Prepare Postgres for CI (service container has no compose init). Creates app/ro roles + grants.
# Uses the API environment's psycopg so CI does not depend on an apt-installed psql client.
# Expects owner: kame_apply / kame_apply_local_only @ 127.0.0.1:5442 (override via PG*).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT/apps/api"

uv run python - <<'PY'
import os

import psycopg

host = os.environ.get("PGHOST", "127.0.0.1")
port = int(os.environ.get("PGPORT", "5442"))
user = os.environ.get("PGUSER", "kame_apply")
password = os.environ.get("PGPASSWORD", "kame_apply_local_only")

with psycopg.connect(
    host=host, port=port, user=user, password=password, dbname="postgres", autocommit=True
) as conn, conn.cursor() as cur:
    cur.execute(
        """
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
        """
    )
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'kame_apply_test'")
    if cur.fetchone() is None:
        cur.execute("CREATE DATABASE kame_apply_test OWNER kame_apply")
    cur.execute(
        "GRANT CONNECT ON DATABASE kame_apply_test TO kame_apply_app, kame_apply_ro"
    )

with psycopg.connect(
    host=host,
    port=port,
    user=user,
    password=password,
    dbname="kame_apply_test",
    autocommit=True,
) as conn, conn.cursor() as cur:
    cur.execute("GRANT USAGE ON SCHEMA public TO kame_apply_app, kame_apply_ro")
    cur.execute(
        """
        ALTER DEFAULT PRIVILEGES FOR ROLE kame_apply IN SCHEMA public
          GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO kame_apply_app;
        ALTER DEFAULT PRIVILEGES FOR ROLE kame_apply IN SCHEMA public
          GRANT USAGE, SELECT ON SEQUENCES TO kame_apply_app;
        ALTER DEFAULT PRIVILEGES FOR ROLE kame_apply IN SCHEMA public
          GRANT SELECT ON TABLES TO kame_apply_ro;
        """
    )

print("OK — CI Postgres roles ready")
PY
