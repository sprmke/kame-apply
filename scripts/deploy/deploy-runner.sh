#!/usr/bin/env bash
# deploy:runner:dev|prod — build the cloud runner image and refresh the Compose service.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=./prod-unlock.sh
source "$ROOT/scripts/deploy/prod-unlock.sh"

ENV_NAME="${1:-}"
if [[ -z "$ENV_NAME" ]]; then
  echo "Usage: deploy-runner.sh <dev|prod>" >&2
  exit 2
fi
if [[ "$ENV_NAME" == "prod" ]]; then
  require_prod_unlock "deploy:runner:prod"
fi

IMAGE="${KAME_RUNNER_IMAGE:-kame-apply-runner:$(git -C "$ROOT" rev-parse --short HEAD)}"
echo "Building $IMAGE"
docker build -t "$IMAGE" -f "$ROOT/apps/runner/Dockerfile" "$ROOT"

if [[ -n "${DEPLOY_HOST:-}" ]]; then
  echo "Syncing compose to $DEPLOY_HOST"
  rsync -az "$ROOT/infra/" "$DEPLOY_HOST:/opt/kame-apply/infra/"
  if [[ -n "${KAME_REGISTRY:-}" ]]; then
    REMOTE_IMAGE="${KAME_REGISTRY%/}/kame-apply-runner:$(git -C "$ROOT" rev-parse --short HEAD)"
    docker tag "$IMAGE" "$REMOTE_IMAGE"
    docker push "$REMOTE_IMAGE"
    ssh "$DEPLOY_HOST" "cd /opt/kame-apply/infra && KAME_RUNNER_IMAGE=$REMOTE_IMAGE docker compose -f docker-compose.prod.yml pull runner"
  else
    docker save "$IMAGE" | ssh "$DEPLOY_HOST" "docker load"
  fi
  ssh "$DEPLOY_HOST" "cd /opt/kame-apply/infra && KAME_RUNNER_IMAGE=$IMAGE docker compose -f docker-compose.prod.yml up -d runner"
else
  echo "DEPLOY_HOST unset — image built locally as $IMAGE"
  echo "On the VM: KAME_RUNNER_IMAGE=$IMAGE docker compose -f infra/docker-compose.prod.yml up -d runner"
fi
echo "OK deploy-runner $ENV_NAME"
