#!/usr/bin/env bash
# Point Compose at a previous API image tag. Prod requires APPLYWAVE=applywave.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=./prod-unlock.sh
source "$ROOT/scripts/deploy/prod-unlock.sh"

ENV_NAME="${1:-}"
IMAGE="${2:-}"
if [[ -z "$ENV_NAME" || -z "$IMAGE" ]]; then
  echo "Usage: rollback-api.sh <dev|prod> <image:tag>" >&2
  exit 2
fi
if [[ "$ENV_NAME" == "prod" ]]; then
  require_prod_unlock "deploy:api:prod rollback $IMAGE"
fi
: "${DEPLOY_HOST:?Set DEPLOY_HOST}"

ssh "$DEPLOY_HOST" "cd /opt/kame-apply/infra && KAME_API_IMAGE=$IMAGE docker compose -f docker-compose.prod.yml up -d api"
echo "OK rollback-api $ENV_NAME → $IMAGE"
