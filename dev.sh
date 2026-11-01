#!/usr/bin/env bash
# Run Postgres/MinIO/Mailpit (docker), apply migrations, then API + web together.
set -euo pipefail
cd "$(dirname "$0")"
pnpm run dev:docker
pnpm run db:migrate
trap 'kill 0' EXIT INT TERM
pnpm run dev:api &
pnpm run dev:web &
wait
