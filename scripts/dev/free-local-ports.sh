#!/usr/bin/env bash
# Stop stale Kame Apply dev listeners so strictPort / uvicorn can bind.
set -euo pipefail

PORTS=(3100 8100)

for port in "${PORTS[@]}"; do
  pids=$(lsof -ti "tcp:${port}" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -z "$pids" ]]; then
    continue
  fi
  echo "free-local-ports: stopping PID(s) on :${port} — ${pids//$'\n'/ }"
  # shellcheck disable=SC2086
  kill $pids 2>/dev/null || true
  sleep 0.3
  remaining=$(lsof -ti "tcp:${port}" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "$remaining" ]]; then
    # shellcheck disable=SC2086
    kill -9 $remaining 2>/dev/null || true
  fi
done
