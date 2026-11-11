#!/usr/bin/env bash
# migrate:host:dev|prod — run Alembic inside the API container over SSH.
# The Compose Postgres is not exposed publicly; this keeps migrations on the host network.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=./prod-unlock.sh
source "$ROOT/scripts/deploy/prod-unlock.sh"

ENV_NAME="${1:-}"
if [[ -z "$ENV_NAME" ]]; then
  echo "Usage: migrate-host.sh <dev|prod>" >&2
  exit 2
fi
if [[ "$ENV_NAME" == "prod" ]]; then
  require_prod_unlock "migrate:host:prod"
fi
: "${DEPLOY_HOST:?Set DEPLOY_HOST to the SSH host running Compose}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

echo "Running migrations in the API container on $DEPLOY_HOST"
ssh "$DEPLOY_HOST" \
  "cd /opt/kame-apply/infra && docker compose -f $COMPOSE_FILE exec -T api uv run alembic upgrade head"
echo "OK migrate-host $ENV_NAME"
