#!/usr/bin/env bash
# PreToolUse hook (matcher: Bash): allow/deny/ask for shell commands before they run.
# Reads Claude Code's PreToolUse JSON from stdin: {"tool_input": {"command": "..."}, ...}
# Outputs hookSpecificOutput.permissionDecision: allow | deny | ask | defer.

set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=scripts/dev/prod-deploy-guard-lib.sh
source "$ROOT/scripts/dev/prod-deploy-guard-lib.sh"

input=$(cat)
if command -v jq >/dev/null 2>&1; then
  command_str=$(echo "$input" | jq -r '.tool_input.command // empty')
else
  command_str=$(echo "$input" | grep -o '"command":"[^"]*"' | head -1 | sed 's/"command":"//;s/"$//' | sed 's/\\"/"/g')
fi

decision=""
reason=""

if prod_deploy_is_blocked "$command_str"; then
  decision="deny"
  reason=$(prod_deploy_block_reason)
else
  case "$command_str" in
    *"rm -rf /"*|*"rm -rf /*"*|*"rm -rf ~"*)
      decision="deny"
      reason="Blocked: recursive delete of root or home is not allowed. Use a specific path instead."
      ;;
    *"drop table"*|*"DROP TABLE"*)
      decision="ask"
      reason="This command may drop database tables. Confirm before running."
      ;;
    *"db:reset:local"*|*"docker compose down -v"*|*"docker-compose down -v"*)
      decision="ask"
      reason="This deletes local Docker/Postgres data volumes. Confirm this is intended before running."
      ;;
    *".env.production"*)
      case "$command_str" in
        *">"*|*"tee "*|*"cp "*|*"mv "*|*"sed -i"*)
          decision="deny"
          reason="Blocked: writing .env.production* is not allowed from an agent session. Edit production secrets by hand."
          ;;
      esac
      ;;
    *"push --force"*|*"push -f"*)
      case "$command_str" in
        *" main"*|*" master"*)
          decision="deny"
          reason="Blocked: force-push to main/master is not allowed."
          ;;
        *)
          decision="ask"
          reason="Force-push can overwrite remote history / a collaborator's work. Confirm before running."
          ;;
      esac
      ;;
    *"git add"*".env"*)
      decision="ask"
      reason="Staging a .env file risks committing secrets. Confirm."
      ;;
    *)
      ;;
  esac
fi

if [[ -n "$decision" ]]; then
  if command -v jq >/dev/null 2>&1; then
    jq -n --arg decision "$decision" --arg reason "$reason" \
      '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: $decision, permissionDecisionReason: $reason}}'
  else
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"%s","permissionDecisionReason":"%s"}}' "$decision" "$reason"
  fi
else
  echo '{}'
fi
