#!/usr/bin/env bash
# Deterministic design-slop sweep (anti-slop-design.mdc). Anything a script can decide is not left
# to review judgment. Scans app and UI source, not tokens.css (the one place raw colors live).
set -euo pipefail
cd "$(dirname "$0")/../.."
DIRS=(apps/web/app packages/ui/src apps/extension)
FILES=$(grep -rIl --include='*.vue' --include='*.ts' --include='*.css' --exclude='tokens.css' --exclude-dir=node_modules --exclude-dir=.nuxt --exclude-dir=.output --exclude-dir=.wxt -e '' "${DIRS[@]}" 2>/dev/null || true)
fail=0
check() { # name, regex, [allow-regex applied to matching lines]
  local name="$1" re="$2" allow="${3:-}" hits
  hits=$(echo "$FILES" | xargs grep -nE "$re" 2>/dev/null | { if [[ -n "$allow" ]]; then grep -vE "$allow" || true; else cat; fi; } || true)
  if [[ -n "$hits" ]]; then echo "FAIL: $name"; echo "$hits" | sed 's/^/  /'; fail=1; fi
}
check "raw hex colors (use tokens)" '#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b' '(href=|url\(|&#|"#main"|#main|id=|:to=|to="#)'
check "gradients, blur, glow" '(bg-gradient|linear-gradient|radial-gradient|backdrop-blur|blur-|drop-shadow|shadow-(sm|md|lg|xl|2xl))' 'mask-image'
check "forbidden icon sets" 'lucide|sparkle|:sparkles'
check "default-palette or off-brand accent classes" '\b(bg|text|border|ring|fill|stroke)-(teal|indigo|blue|sky|cyan|violet|purple|pink|emerald|green|red|slate|gray|zinc|neutral|stone)-[0-9]{2,3}\b'
check "em dashes in UI source" '\xe2\x80\x94'
# One persimmon per view: fills are allowed only in the primary button, route line, rail, brand mark,
# Needs-you plate, checkbox state, the single emphasis series in charts, and the style guide.
check "brand fill outside its allowlist" '(bg|fill)-brand-500' '(FnButton|FnRouteLine|FnCheckbox|BrandMark|AppRail|MobileBar|UsageChart|_design|tokens)'
# Touch targets: interactive controls must be 44px (min-h-11). Smaller only behind a breakpoint.
check "touch target under 44px" 'min-h-(8|9|10)\b' 'md:min-h-'
if [[ $fail -ne 0 ]]; then echo; echo "design-slop check failed"; exit 1; fi
echo "OK — design-slop check"
