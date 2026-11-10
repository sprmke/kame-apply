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
APP_ENV="prod"
if [[ "$ENV_NAME" == "dev" ]]; then
  APP_ENV="dev"
fi
echo "Building $IMAGE (ENVIRONMENT=$APP_ENV)"
docker build -t "$IMAGE" -f "$ROOT/apps/api/Dockerfile" "$ROOT"

if [[ -n "${DEPLOY_HOST:-}" ]]; then
  echo "Syncing compose to $DEPLOY_HOST"
  rsync -az "$ROOT/infra/" "$DEPLOY_HOST:/opt/kame-apply/infra/"
  if [[ -n "${KAME_REGISTRY:-}" ]]; then
    REMOTE_IMAGE="${KAME_REGISTRY%/}/kame-apply-api:$(git -C "$ROOT" rev-parse --short HEAD)"
    docker tag "$IMAGE" "$REMOTE_IMAGE"
    echo "Pushing $REMOTE_IMAGE"
    docker push "$REMOTE_IMAGE"
    ssh "$DEPLOY_HOST" "cd /opt/kame-apply/infra && KAME_ENVIRONMENT=$APP_ENV KAME_API_IMAGE=$REMOTE_IMAGE docker compose -f docker-compose.prod.yml pull api"
  else
    # No registry configured: ship the image over SSH instead of pretending `pull` worked.
    echo "Transferring $IMAGE to $DEPLOY_HOST"
    docker save "$IMAGE" | ssh "$DEPLOY_HOST" "docker load"
  fi
  ssh "$DEPLOY_HOST" "cd /opt/kame-apply/infra && API_HOST=${API_HOST:-api.kame.apply} KAME_ENVIRONMENT=$APP_ENV KAME_API_IMAGE=$IMAGE docker compose -f docker-compose.prod.yml up -d api caddy"
  if [[ -n "${DEPLOY_HEALTH_URL:-}" ]]; then
    for i in $(seq 1 30); do
      if curl -fsS "$DEPLOY_HEALTH_URL" >/dev/null; then
        echo "Health check passed"
        break
      fi
      if [[ "$i" == "30" ]]; then
        echo "Health check failed: $DEPLOY_HEALTH_URL" >&2
        exit 1
      fi
      sleep 2
    done
  else
    echo "DEPLOY_HEALTH_URL unset — skipping the post-deploy health check"
  fi
else
  echo "DEPLOY_HOST unset — image built locally as $IMAGE"
  echo "On the VM: KAME_API_IMAGE=$IMAGE docker compose -f infra/docker-compose.prod.yml up -d api caddy"
fi
echo "OK deploy-api $ENV_NAME"
