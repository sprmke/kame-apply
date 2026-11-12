#!/usr/bin/env bash
# Fail when a component or composable branches on an industry key. Packs are data; pages read the
# resolved manifest from the API. Base-key handling ("general") is allowed.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if ! command -v rg >/dev/null 2>&1; then
  echo "OK — industry branch check skipped (ripgrep not installed)"
  exit 0
fi

MATCHES="$(rg -n --glob '*.vue' --glob '*.ts' \
  '(\bindustry[[:space:]]*===|\bindustry[[:space:]]*==|pack\.key[[:space:]]*===|pack\.key[[:space:]]*==)' \
  apps/web/app || true)"

if [[ -n "$MATCHES" ]]; then
  echo "$MATCHES"
  echo
  echo "Components must not branch on an industry key. Read useExperience() state, labels, or facets."
  exit 1
fi

echo "OK — no industry branches in web components"
