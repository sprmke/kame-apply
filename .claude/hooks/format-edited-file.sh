#!/usr/bin/env bash
# PostToolUse hook (Edit|Write): ruff for Python, Prettier for TS/Vue/MD/JSON/CSS.
# Purely cosmetic; never blocks the edit.
set -e
input=$(cat)
if command -v jq >/dev/null 2>&1; then
  file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty')
else
  file_path=$(echo "$input" | grep -o '"file_path":"[^"]*"' | head -1 | sed 's/"file_path":"//;s/"$//')
fi

if [[ -n "$file_path" && -f "$file_path" ]]; then
  case "$file_path" in
    *.py)
      if command -v uv >/dev/null 2>&1; then
        (cd "$(dirname "$file_path")" && uv run --quiet ruff format "$file_path" && uv run --quiet ruff check --fix --quiet "$file_path") >/dev/null 2>&1 || true
      elif command -v ruff >/dev/null 2>&1; then
        ruff format "$file_path" >/dev/null 2>&1 || true
        ruff check --fix --quiet "$file_path" >/dev/null 2>&1 || true
      fi ;;
    *.ts|*.tsx|*.js|*.mjs|*.vue|*.json|*.md|*.mdc|*.css|*.html|*.yml|*.yaml)
      # Only when the repo has Prettier installed locally (no network fetch).
      if [[ -d node_modules/prettier ]] && command -v pnpm >/dev/null 2>&1; then
        pnpm exec prettier --write "$file_path" >/dev/null 2>&1 || true
      fi ;;
  esac
fi
echo '{}'
