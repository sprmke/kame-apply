#!/usr/bin/env bash
# PreToolUse hook: never edit a shipped Alembic migration — add a new one.
# See .cursor/rules/migrations.mdc

set -e
input=$(cat)
if command -v jq >/dev/null 2>&1; then
  file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')
else
  file_path=$(echo "$input" | grep -o '"file_path":"[^"]*"' | head -1 | sed 's/"file_path":"//;s/"$//')
fi

if [[ -f "$file_path" ]] &&
  [[ "$file_path" == *"/apps/api/migrations/versions/"* || "$file_path" == apps/api/migrations/versions/* ]]; then
  reason="Editing a shipped migration under apps/api/migrations/versions/ is not allowed — add a new migration instead (see .cursor/rules/migrations.mdc)."
  if command -v jq >/dev/null 2>&1; then
    jq -n --arg reason "$reason" \
      '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
  else
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}' "$reason"
  fi
else
  echo '{}'
fi
