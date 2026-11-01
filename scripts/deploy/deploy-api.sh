#!/usr/bin/env bash
# deploy:api:dev|prod — build/push API image and refresh Compose on the host.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=./prod-unlock.sh
source "$ROOT/scripts/deploy/prod-unlock.sh"

ENV_NAME="${1:-}"
if [[ -z "$ENV_NAME" ]]; then
  echo "Usage: deploy-api.sh <dev|prod>" >&2
  exit 2
fi
if [[ "$ENV_NAME" == "prod" ]]; then
  require_prod_unlock "deploy:api:prod"
fi

IMAGE="${KAME_API_IMAGE:-kame-apply-api:$(git -C "$ROOT" rev-parse --short HEAD)}"
echo "Building $IMAGE"
docker build -t "$IMAGE" -f "$ROOT/apps/api/Dockerfile" "$ROOT"

if [[ -n "${DEPLOY_HOST:-}" ]]; then
  echo "Syncing compose to $DEPLOY_HOST"
  rsync -az "$ROOT/infra/" "$DEPLOY_HOST:/opt/kame-apply/infra/"
  ssh "$DEPLOY_HOST" "cd /opt/kame-apply/infra && KAME_API_IMAGE=$IMAGE docker compose -f docker-compose.prod.yml pull api || true && KAME_API_IMAGE=$IMAGE docker compose -f docker-compose.prod.yml up -d api caddy"
else
  echo "DEPLOY_HOST unset — image built locally as $IMAGE"
  echo "On the VM: KAME_API_IMAGE=$IMAGE docker compose -f infra/docker-compose.prod.yml up -d api caddy"
fi
echo "OK deploy-api $ENV_NAME"
