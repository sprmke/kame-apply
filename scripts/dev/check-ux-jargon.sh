#!/usr/bin/env bash
# UX clarity: no internal words in user-facing strings, and no hardcoded
# user-facing attributes that bypass i18n.
#
# Scope:
#   apps/web/i18n/locales/en.json        (every value)
#   apps/extension/**/locales/*.json      (every value)
#   apps/web/app/**/*.vue                 (text inside <template>)
#   apps/extension/**/*.vue               (text inside <template>)
#
# Allowlisted files: legal pages, the design guide, admin-only ops pages
# (they define the metric on the same screen), and docs.
#
# Usage: pnpm run check:ux-jargon            (blocking)
#        UX_JARGON_ENFORCE=0 pnpm run check:ux-jargon   (warn only)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

ENFORCE="${UX_JARGON_ENFORCE:-1}"

# Internal word -> user word. Keep in sync with docs/design/glossary.md.
#
# Matching is case-insensitive and word-bounded. "track" as a verb ("track your
# applications") is legitimate English, so the pattern requires the product
# sense: Track as a noun, or the exact labels listed.
BANNED='(\bautonomy\b|\bdry[- ]runs?\b|\bkill switch\b|\bscore threshold\b|\bcircuit open\b|\bfit ledger\b|\bMCP\b|\btenant\b|\bpayload\b|\bleased?\b|\bclassify\b|\blatency\b|\bquotas?\b|\bATS\b|\bCandidates\b|\bInterview prep\b|\bAnswer Desk\b|\bModels? by tier\b|\bScore threshold\b|\bFreq\b|a Track\b|\bTrack sections\b|another Track\b|from track\b|this Track\b|\bPick a Track\b|\bInclude ineligible\b|\bIneligible\b|\bRun critique\b|\bRun insights\b|\bPick a resume\b)'

ALLOW_FILES=(
  'apps/web/app/pages/legal/'
  'apps/web/app/pages/_design.vue'
  'apps/web/app/pages/settings/sources.vue'
  'apps/web/app/pages/settings/ops.vue'
  'apps/web/app/pages/settings/activity.vue'
)

is_allowed() {
  local f="$1"
  for p in "${ALLOW_FILES[@]}"; do [[ "$f" == "$p"* ]] && return 0; done
  return 1
}

V=0
report() { # file line text
  echo "  $1:$2: $3"
}

# Strip a JSON value's key so we only read the value, and ignore keys such as
# "tracks" (code-facing) and paths.
scan_json() {
  local file="$1"
  local out
  out=$(grep -nE '"[^"]+"[[:space:]]*:' "$file" | grep -vE '^[0-9]+:[[:space:]]*"[a-z0-9_.-]+"[[:space:]]*:[[:space:]]*\{' || true)
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    local no="${line%%:*}"
    local text
    text=$(echo "${line#*:}" | sed 's/^[[:space:]]*"[^"]*"[[:space:]]*:[[:space:]]*//')
    if echo "$text" | grep -qiE "$BANNED"; then
      report "$file" "$no" "$(echo "$text" | sed 's/^[[:space:]]*//' | cut -c1-140)"
      V=$((V + 1))
    fi
  done <<<"$out"
}

# Render text between <template> and </template>, skipping attributes that are
# already bound. This catches hardcoded product words in visible copy.
scan_vue() {
  local file="$1"
  local body
  body=$(awk '/<template>/{on=1} on{print NR": "$0} /<\/template>/{if(on){on=0}}' "$file" \
    | grep -vE '\{\{|:[a-z-]+=|v-|\{\{#|\{\{/|<!--' \
    | grep -vE '\bt\(|[=!]==|&&|\|\||\.value\b|^[0-9]+: *(//|/\*)' || true)
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    local no="${line%%:*}"
    local text
    text=$(echo "${line#*:}" | sed 's/^[[:space:]]*"[^"]*"[[:space:]]*:[[:space:]]*//')
    if echo "$text" | grep -qiE "$BANNED"; then
      report "$file" "$no" "$(echo "$text" | sed 's/^[[:space:]]*//' | cut -c1-140)"
      V=$((V + 1))
    fi
  done <<<"$body"
}

echo "→ scanning user-facing strings for internal words"
while IFS= read -r f; do
  is_allowed "$f" && continue
  scan_json "$f"
done < <(find apps/web/i18n apps/extension -path '*locales*' -name '*.json' 2>/dev/null | sort)

while IFS= read -r f; do
  is_allowed "$f" && continue
  scan_vue "$f"
done < <(find apps/web/app apps/extension -name '*.vue' -not -path '*/node_modules/*' 2>/dev/null | sort)

echo "→ scanning for hardcoded user-facing attributes"
ATTR=0
while IFS= read -r f; do
  is_allowed "$f" && continue
  # The extension has no vue-i18n; its strings are compiled into the panel.
  [[ "$f" == apps/extension/* ]] && continue
  hits=$(grep -nE '(^|[^:a-z-])(aria-label|placeholder|title)="[A-Z][^"]{3,}"' "$f" | grep -vE '\{\{|t\(' || true)
  if [[ -n "$hits" ]]; then
    while IFS= read -r h; do report "$f" "${h%%:*}" "$(echo "$h" | cut -c1-140)"; ATTR=$((ATTR + 1)); done <<<"$hits"
  fi
done < <(find apps/web/app apps/extension -name '*.vue' -not -path '*/node_modules/*' 2>/dev/null | sort)

if [[ "$V" -gt 0 || "$ATTR" -gt 0 ]]; then
  echo ""
  echo "$V internal word(s), $ATTR hardcoded attribute(s)."
  echo "Use the user word from docs/design/glossary.md and move strings into i18n."
  [[ "$ENFORCE" == "1" ]] && exit 1
  echo "warn only (UX_JARGON_ENFORCE=0)"
  exit 0
fi
echo "OK — plain words"
