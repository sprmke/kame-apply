#!/usr/bin/env bash
set -euo pipefail
ENV_FILE="apps/api/.env"
if [[ -f "$ENV_FILE" ]]; then
  echo "apps/api/.env present"
  grep -E '^DATABASE_URL=|^ENVIRONMENT=' "$ENV_FILE" || true
else
  echo "apps/api/.env missing — copy from .env.example"
fi
