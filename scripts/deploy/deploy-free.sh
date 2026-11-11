#!/usr/bin/env bash
# deploy:free — one VM, one DuckDNS name, Caddy static web + API, MinIO, SMTP.
# No domain purchase, Cloudflare Pages, R2, or Resend required.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=./prod-unlock.sh
source "$ROOT/scripts/deploy/prod-unlock.sh"

: "${DEPLOY_HOST:?Set DEPLOY_HOST to the SSH host running Docker Compose}"
: "${API_HOST:?Set API_HOST to the DuckDNS name, for example kame.duckdns.org}"
: "${S3_HOST:?Set S3_HOST to the second DuckDNS name, for example kame-s3.duckdns.org}"

IMAGE="${KAME_API_IMAGE:-kame-apply-api:$(git -C "$ROOT" rev-parse --short HEAD)}"
echo "Building $IMAGE (ENVIRONMENT=dev)"
docker build -t "$IMAGE" -f "$ROOT/apps/api/Dockerfile" "$ROOT"

echo "Syncing compose and Caddy config to $DEPLOY_HOST"
rsync -az "$ROOT/infra/" "$DEPLOY_HOST:/opt/kame-apply/infra/"

if [[ -n "${KAME_REGISTRY:-}" ]]; then
  REMOTE_IMAGE="${KAME_REGISTRY%/}/kame-apply-api:$(git -C "$ROOT" rev-parse --short HEAD)"
  docker tag "$IMAGE" "$REMOTE_IMAGE"
  echo "Pushing $REMOTE_IMAGE"
  docker push "$REMOTE_IMAGE"
  ssh "$DEPLOY_HOST" "cd /opt/kame-apply/infra && KAME_API_IMAGE=$REMOTE_IMAGE docker compose -f docker-compose.free.yml pull api"
  RUN_IMAGE="$REMOTE_IMAGE"
else
  echo "Transferring $IMAGE to $DEPLOY_HOST"
  docker save "$IMAGE" | ssh "$DEPLOY_HOST" "docker load"
  RUN_IMAGE="$IMAGE"
fi

echo "Building the static web app against https://$API_HOST"
cd "$ROOT"
NUXT_PUBLIC_API_BASE="https://$API_HOST" pnpm --filter @kame/web run generate
OUT="$ROOT/apps/web/.output/public"
if [[ ! -d "$OUT" ]]; then
  OUT="$ROOT/apps/web/dist"
fi
ssh "$DEPLOY_HOST" "mkdir -p /opt/kame-apply/infra/web"
rsync -az --delete "$OUT/" "$DEPLOY_HOST:/opt/kame-apply/infra/web/"

echo "Starting the free profile on $DEPLOY_HOST"
ssh "$DEPLOY_HOST" \
  "cd /opt/kame-apply/infra && API_HOST=$API_HOST S3_HOST=$S3_HOST KAME_ENVIRONMENT=dev KAME_API_IMAGE=$RUN_IMAGE docker compose -f docker-compose.free.yml up -d"

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

cat <<EOF
OK deploy-free
Next, create the app role and run migrations:
  export COMPOSE_FILE=docker-compose.free.yml
  export APP_DB_PASSWORD=<the app password in DATABASE_URL>
  pnpm run db:roles:host:dev
  pnpm run migrate:host:dev
EOF
