#!/usr/bin/env bash
# Move a workflow doc between lifecycle folders under docs/workflow/.
# Usage: workflow-move.sh <start|done|wont-do> <slug>
# Moves <slug>.md (and <slug>-design.md if present) and prints the index rows to update.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
W="$ROOT/docs/workflow"
action="${1:-}"; slug="${2:-}"
[[ -n "$action" && -n "$slug" ]] || { echo "usage: $0 <start|done|wont-do> <slug>"; exit 1; }
[[ "$slug" =~ ^[a-z0-9][a-z0-9-]*$ ]] || { echo "slug must be kebab-case (no date prefix): $slug"; exit 1; }

case "$action" in
  start) dest="in-progress"; froms=(planned intake) ;;
  done) dest="done"; froms=(in-progress planned) ;;
  wont-do) dest="wont-do"; froms=(planned in-progress intake) ;;
  *) echo "unknown action: $action"; exit 1 ;;
esac

moved=0
for name in "$slug.md" "$slug-design.md"; do
  for from in "${froms[@]}"; do
    if [[ -f "$W/$from/$name" ]]; then
      mkdir -p "$W/$dest"
      mv "$W/$from/$name" "$W/$dest/$name"
      echo "moved docs/workflow/$from/$name → docs/workflow/$dest/$name"
      moved=1
      break
    fi
  done
done
[[ $moved -eq 1 ]] || { echo "no workflow doc found for slug '$slug' in: ${froms[*]}"; exit 1; }
echo "Now update the index tables: docs/workflow/*/README.md (remove the old row, add one under $dest)."
