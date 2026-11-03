#!/usr/bin/env bash
# PostToolUse: warn on out-of-scope stack drift and FAIL LOUDLY on bot-evasion tooling.
# Evasion tooling (PRD P2) is never allowed in code, manifests, or lockfiles.
set -e
input=$(cat)
if command -v jq >/dev/null 2>&1; then
  file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')
else
  file_path=""
fi

[[ -n "$file_path" && -f "$file_path" ]] || { echo '{}'; exit 0; }

# Docs and tooling files may name banned things in order to forbid them.
case "$file_path" in
  *.md|*.mdc|*/docs/*|*/.agent/*|*/.cursor/*|*/.claude/*|*/.opencode/*|*/scripts/dev/*|*/opencode.json) echo '{}'; exit 0 ;;
esac

EVASION='playwright-stealth|playwright_stealth|undetected[-_]chromedriver|undetected[-_]playwright|puppeteer-extra-plugin-stealth|camoufox|capsolver|2captcha|anticaptcha|anti-captcha|deathbycaptcha|fake[-_]useragent|rotating[-_]proxy|proxy[-_]rotat|brightdata|luminati|scrapingbee|zenrows|flaresolverr|cloudscraper'
STACK='from react|"react"|react-dom|next/|@tanstack/react|@tanstack/start|shadcn|lucide|@supabase/|drizzle-orm|@prisma/client|\barq\b|from arq|import redis|tRPC|trpc'

decision_msg=""
if grep -qiE "$EVASION" "$file_path" 2>/dev/null; then
  decision_msg="BLOCKED CONTENT in $file_path: bot-evasion tooling (stealth plugins, CAPTCHA solvers, proxy rotation, fingerprint spoofing) is forbidden by PRD P2 and .cursor/rules/job-site-access.mdc. Remove it and use the compliant path (ATS APIs, public feeds, extension in the user's session, live takeover)."
  kind="evasion"
else
  case "$file_path" in
    */apps/web/*|*/apps/extension/*|*/packages/ui/*|*/apps/api/*|*/packages/*)
      if grep -qE "$STACK" "$file_path" 2>/dev/null; then
        decision_msg="Possible out-of-scope stack in $file_path. Kame Apply uses FastAPI + SQLAlchemy + DBOS + Vue 3/Nuxt 4 + Phosphor + Reka UI (docs/tech-stack.md §6). Employer-form adapters may mention React widgets; nothing else should."
      fi ;;
  esac
  kind="stack"
fi

if [[ -n "$decision_msg" ]]; then
  if command -v jq >/dev/null 2>&1; then
    jq -n --arg reason "$decision_msg" '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $reason}}'
  else
    printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"%s"}}' "$decision_msg"
  fi
  [[ "$kind" == "evasion" ]] && echo "$decision_msg" >&2 && exit 2
  exit 0
fi
echo '{}'
