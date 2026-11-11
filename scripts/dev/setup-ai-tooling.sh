#!/usr/bin/env bash
# One-shot post-clone AI tooling setup. Idempotent.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

printf -- '-> AI tooling (links, OpenCode agents, Codex layer, drift check)\n'
python3 "$ROOT/scripts/dev/ai-tooling.py" wire

printf -- '-> Required CLIs\n'
for tool in jq git node pnpm uv docker; do
  command -v "$tool" >/dev/null 2>&1 && printf '   ok  %s\n' "$tool" || printf '   !!  %s not found\n' "$tool" >&2
done

printf -- '-> Optional tools\n'
command -v markitdown-mcp >/dev/null 2>&1 \
  && printf '   ok  markitdown-mcp on PATH\n' \
  || printf '   !!  markitdown-mcp not on PATH - uv tool install markitdown-mcp\n' >&2

printf '\nAI tooling ready. Re-run: pnpm run setup:ai-tooling\n'
