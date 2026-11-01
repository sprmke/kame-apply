#!/usr/bin/env bash
# Capture design-review screenshots against a running local app (seeded DB).
# Usage: pnpm run dev  (in another terminal) → pnpm run capture:design-screenshots
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT/apps/web"
export CAPTURE_DESIGN_SCREENSHOTS=1
export DESIGN_SCREENSHOT_BASE_URL="${DESIGN_SCREENSHOT_BASE_URL:-http://127.0.0.1:3100}"
mkdir -p "$ROOT/.audit-screenshots/harness"
echo "→ capturing to .audit-screenshots/harness/ (gitignored)"
echo "  base URL: $DESIGN_SCREENSHOT_BASE_URL"
echo "  login: ${DESIGN_SCREENSHOT_EMAIL:-demo@example.com}"
pnpm exec playwright test --config=playwright.screenshots.config.ts
echo "OK — screenshots written under .audit-screenshots/harness/"
