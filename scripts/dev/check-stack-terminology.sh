#!/usr/bin/env bash
# Repo-wide scan (CI): no bot-evasion tooling anywhere in code or manifests, and no
# out-of-scope frameworks in our own frontend/backend manifests. Docs/tooling files are exempt
# because they name the banned things in order to forbid them.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

EVASION='playwright-stealth|playwright_stealth|undetected[-_]chromedriver|undetected[-_]playwright|puppeteer-extra-plugin-stealth|camoufox|capsolver|2captcha|anticaptcha|anti-captcha|deathbycaptcha|fake[-_]useragent|rotating[-_]proxy|proxy[-_]rotat|brightdata|luminati|scrapingbee|zenrows|flaresolverr|cloudscraper'
STACK_MANIFEST='"react"|"react-dom"|"next"|"@tanstack/react-[a-z-]+"|"@tanstack/start|"lucide-[a-z-]+"|"@supabase/[a-z-]+"|"drizzle-orm"|"@prisma/client"|"@trpc/[a-z-]+"|shadcn'
PY_STACK='^\s*"?(arq|redis|prisma|supabase)[">= ]'

V=0
scan() { # label pattern files...
  local label="$1" pat="$2"; shift 2
  local hits
  hits=$( { grep -rniE "$pat" "$@" 2>/dev/null || true; } | head -20)
  if [[ -n "$hits" ]]; then echo "VIOLATION ($label):"; echo "$hits"; V=$((V + 1)); fi
}

EXCLUDES=(--exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=.git --exclude-dir=docs --exclude-dir=.agent --exclude-dir=.cursor --exclude-dir=.claude --exclude-dir=.opencode --exclude-dir=scripts --exclude-dir=.nuxt --exclude-dir=.output --exclude-dir=.wxt --exclude=opencode.json --exclude=CLAUDE.md --exclude=README.md --exclude=*.md --exclude=*.mdc)

scan "bot-evasion tooling" "$EVASION" "${EXCLUDES[@]}" .

for m in apps/web/package.json apps/extension/package.json packages/ui/package.json; do
  [[ -f "$m" ]] && scan "out-of-scope frontend stack in $m" "$STACK_MANIFEST" "$m"
done
for m in apps/api/pyproject.toml packages/py-core/pyproject.toml; do
  [[ -f "$m" ]] && scan "out-of-scope backend stack in $m" "$PY_STACK" "$m"
done

# Phase 12b: never collect/store/relay Claude credentials on the server or in web config.
CLAUDE_CREDS='CLAUDE_CODE_OAUTH_TOKEN|claude\.ai.*(password|session)|ANTHROPIC_USER_TOKEN'
scan "claude credentials in server/web/plugin/cli" "$CLAUDE_CREDS" \
  --exclude-dir=__pycache__ --exclude-dir=.venv --exclude-dir=node_modules \
  --exclude='*.md' --exclude='*.mdc' \
  apps/api apps/web integrations/claude-plugin packages/kame-agent

[[ "$V" -gt 0 ]] && { echo "$V violation group(s)"; exit 1; }
echo "OK — stack terminology"
