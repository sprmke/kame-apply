#!/usr/bin/env bash
# Naming conventions (.cursor/rules/naming-conventions.mdc). Skips dirs that don't exist yet.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
VIOLATIONS=0
fail() { echo "FILENAME: $1"; VIOLATIONS=$((VIOLATIONS + 1)); }

# Python modules: snake_case.py
while IFS= read -r -d '' f; do
  base="$(basename "$f")"
  case "$base" in __init__.py|env.py|conftest.py) continue ;; esac
  [[ "$base" =~ ^[a-z0-9_]+\.py$ ]] || fail "$f (Python modules must be snake_case.py)"
done < <(find apps/api/app apps/api/tests apps/runner packages/py-core -name '*.py' \
  -not -path '*/.venv/*' -not -path '*/node_modules/*' -print0 2>/dev/null)

# Vue components: PascalCase.vue (Nuxt pages/layouts/app.vue/error.vue are routed by convention)
while IFS= read -r -d '' f; do
  base="$(basename "$f" .vue)"
  case "$f" in
    */pages/*|*/layouts/*|*/entrypoints/*) continue ;;
  esac
  case "$base" in app|error) continue ;; esac
  [[ "$base" =~ ^[A-Z][A-Za-z0-9]*$ ]] || fail "$f (Vue components must be PascalCase.vue)"
done < <(find apps/web apps/extension packages/ui -name '*.vue' \
  -not -path '*/node_modules/*' -not -path '*/.nuxt/*' -not -path '*/.output/*' -not -path '*/.wxt/*' -print0 2>/dev/null)

# TS files: kebab-case.ts, or useX.ts composables, or framework config/generated files
while IFS= read -r -d '' f; do
  base="$(basename "$f")"
  case "$f" in */pages/*|*/entrypoints/*|*/generated/*|*/client/*) continue ;; esac
  case "$base" in
    *.d.ts|nuxt.config.ts|vitest.config.ts|vite.config.ts|wxt.config.ts|playwright*.ts|tailwind.config.ts|eslint.config.*|openapi-ts.config.ts) continue ;;
    use[A-Z]*.ts) continue ;;
  esac
  [[ "$base" =~ ^[a-z0-9]+(-[a-z0-9]+)*(\.[a-z0-9]+)?\.ts$ ]] || fail "$f (TS files must be kebab-case.ts or useX.ts)"
done < <(find apps/web apps/extension packages/ui packages/api-client -name '*.ts' \
  -not -path '*/node_modules/*' -not -path '*/.nuxt/*' -not -path '*/.output/*' -not -path '*/.wxt/*' -not -path '*/dist/*' -print0 2>/dev/null)

[[ "$VIOLATIONS" -gt 0 ]] && { echo "$VIOLATIONS violation(s)"; exit 1; }
echo "OK — filename conventions"
