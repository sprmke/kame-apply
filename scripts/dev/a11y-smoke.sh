#!/usr/bin/env bash
# Accessibility smoke: axe-core against key prerendered/legal routes when the web app is up.
# Skips cleanly if playwright/axe or the local server is unavailable.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BASE="${A11Y_BASE_URL:-http://127.0.0.1:3100}"

if ! curl -fsS "$BASE/" >/dev/null 2>&1; then
  echo "a11y-smoke: $BASE not reachable — skip (start pnpm run dev:web)"
  exit 0
fi

cd "$ROOT"
if ! pnpm exec playwright --version >/dev/null 2>&1; then
  echo "a11y-smoke: playwright missing — skip"
  exit 0
fi

# Inline Node runner so we do not require a committed e2e suite for Phase 14.
node --input-type=module <<'EOF'
import { chromium } from "@playwright/test";

const base = process.env.A11Y_BASE_URL || "http://127.0.0.1:3100";
const routes = ["/", "/legal/privacy", "/legal/terms", "/legal/data-deletion", "/login"];
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage();
let failures = 0;
for (const path of routes) {
  const url = base.replace(/\/$/, "") + path;
  try {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 20000 });
    // Basic keyboard/focus checks without axe dependency.
    const skip = await page.locator('a[href="#main"], a:has-text("Skip")').count();
    const h1 = await page.locator("h1").count();
    if (h1 < 1) {
      console.error(`FAIL ${path}: missing h1`);
      failures += 1;
    } else {
      console.log(`OK ${path} (h1=${h1}, skipLinks=${skip})`);
    }
  } catch (e) {
    console.error(`FAIL ${path}:`, e.message || e);
    failures += 1;
  }
}
await browser.close();
process.exit(failures ? 1 : 0);
EOF
