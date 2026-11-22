#!/usr/bin/env bash
# Stop only this worktree's Nuxt web UI. Never touches another worktree.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PORT_FILE="$ROOT/.local/vite-port"

if [[ ! -f "$PORT_FILE" ]]; then
  echo "No .local/vite-port for this worktree; nothing to stop."
  exit 0
fi

PORT="$(tr -d '[:space:]' <"$PORT_FILE" || true)"
if [[ ! "$PORT" =~ ^[0-9]+$ ]] || ((PORT < 3600 || PORT > 3699)); then
  echo "Invalid sticky port in .local/vite-port; leaving processes alone."
  exit 0
fi

pids="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null || true)"
for pid in $pids; do
  cwd="$(lsof -a -p "$pid" -d cwd 2>/dev/null | awk 'NR==2 { print $NF; exit }')"
  if [[ -n "$cwd" && ( "$cwd" == "$ROOT" || "$cwd" == "$ROOT"/* ) ]]; then
    echo "Stopping worktree UI pid $pid on :$PORT (cwd $cwd)"
    kill "$pid" 2>/dev/null || true
  else
    echo "Listener pid $pid on :$PORT belongs to another cwd ($cwd); not killing."
  fi
done
