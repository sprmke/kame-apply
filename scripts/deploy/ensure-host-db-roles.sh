#!/usr/bin/env bash
# ensure-host-db-roles:dev|prod — create the RLS-restricted app role on the host database.
# The prod Compose does not mount the local init SQL (it creates a known read-only password),
# so the app role is created once here. Safe to re-run; it updates the password.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=./prod-unlock.sh
source "$ROOT/scripts/deploy/prod-unlock.sh"

ENV_NAME="${1:-}"
if [[ -z "$ENV_NAME" ]]; then
  echo "Usage: ensure-host-db-roles.sh <dev|prod>" >&2
  exit 2
fi
if [[ "$ENV_NAME" == "prod" ]]; then
  require_prod_unlock "ensure-host-db-roles:prod"
fi
: "${DEPLOY_HOST:?Set DEPLOY_HOST to the SSH host running Compose}"
: "${APP_DB_PASSWORD:?Set APP_DB_PASSWORD to the kame_apply_app password used in DATABASE_URL}"
POSTGRES_USER="${POSTGRES_USER:-kame_apply}"
POSTGRES_DB="${POSTGRES_DB:-kame_apply}"

tmp="$(mktemp)"
chmod 600 "$tmp"
APP_DB_PASSWORD="$APP_DB_PASSWORD" POSTGRES_DB="$POSTGRES_DB" POSTGRES_USER="$POSTGRES_USER" \
  python3 - >"$tmp" <<'PY'
import os

password = os.environ["APP_DB_PASSWORD"].replace("'", "''")
db = os.environ["POSTGRES_DB"]
owner = os.environ["POSTGRES_USER"]
print(
    f"""
DO $$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'kame_apply_app') THEN
    CREATE ROLE kame_apply_app LOGIN PASSWORD '{password}'
      NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
  ELSE
    ALTER ROLE kame_apply_app PASSWORD '{password}';
  END IF;
END $$;
GRANT CONNECT ON DATABASE {db} TO kame_apply_app;
\\connect {db}
GRANT USAGE ON SCHEMA public TO kame_apply_app;
-- Re-runs must cover tables that already exist (for example when the role was added later).
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO kame_apply_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO kame_apply_app;
ALTER DEFAULT PRIVILEGES FOR ROLE {owner} IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO kame_apply_app;
ALTER DEFAULT PRIVILEGES FOR ROLE {owner} IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO kame_apply_app;
"""
)
PY

echo "Ensuring kame_apply_app on $DEPLOY_HOST"
ssh "$DEPLOY_HOST" \
  "cd /opt/kame-apply/infra && docker compose -f docker-compose.prod.yml exec -T postgres psql -U $POSTGRES_USER -d postgres -v ON_ERROR_STOP=1" \
  <"$tmp"
rm -f "$tmp"
echo "OK ensure-host-db-roles $ENV_NAME"
