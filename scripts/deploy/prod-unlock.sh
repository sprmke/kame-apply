#!/usr/bin/env bash
# Source from deploy scripts. Requires APPLYWAVE=applywave (or the word in the command).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=../dev/prod-deploy-guard-lib.sh
source "$ROOT/scripts/dev/prod-deploy-guard-lib.sh"

require_prod_unlock() {
  local cmd="${APPLYWAVE:-} $* ${PNPM_SCRIPT_SRC:-}"
  if prod_deploy_is_unlocked "$cmd"; then
    return 0
  fi
  prod_deploy_block_reason >&2
  exit 78
}
