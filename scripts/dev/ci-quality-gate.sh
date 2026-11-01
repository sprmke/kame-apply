#!/usr/bin/env bash
# Single quality gate (pnpm run ci:quality). Grows each phase: every step below skips
# cleanly until the thing it checks exists, then becomes mandatory.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

step() { echo; echo "→ $*"; }
has_script() { [[ -f package.json ]] && jq -e --arg s "$1" '.scripts[$s]' package.json >/dev/null 2>&1; }

step "check:ai-tooling-sync"
bash scripts/dev/check-ai-tooling-sync.sh

step "check:tooling-hooks (hook unit checks)"
bash scripts/dev/test-hooks.sh

step "check:filenames"
bash scripts/dev/check-filename-conventions.sh

step "check:stack-terminology (evasion tooling + out-of-scope stack in manifests)"
bash scripts/dev/check-stack-terminology.sh

if [[ -f scripts/dev/check-untrusted-prompts.sh ]]; then
  step "check:untrusted-prompts"
  bash scripts/dev/check-untrusted-prompts.sh
fi

if has_script check:token-contrast; then
  step "check:token-contrast (WCAG pairs in packages/ui tokens)"
  pnpm run check:token-contrast
fi

if [[ -f scripts/dev/check-design-slop.sh ]]; then
  step "check:design-slop"
  bash scripts/dev/check-design-slop.sh
fi

for s in lint format:check type-check build; do
  if has_script "$s"; then step "$s"; pnpm run "$s"; fi
done

if [[ -d apps/api/tests ]] && has_script test:api; then step "pytest"; pnpm run test:api; fi
if has_script check:api-client; then step "api-client drift"; pnpm run check:api-client; fi
if has_script test:web; then step "vitest"; pnpm run test:web; fi
if has_script test:evals-lite; then step "evals-lite"; pnpm run test:evals-lite; fi

echo; echo "OK — ci:quality gate passed"
