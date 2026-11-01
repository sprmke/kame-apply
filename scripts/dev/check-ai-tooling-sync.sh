#!/usr/bin/env bash
# Drift prevention: Cursor, Claude Code, OpenCode AI tooling parity.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
VIOLATIONS=0

fail() { echo "VIOLATION: $1"; VIOLATIONS=$((VIOLATIONS + 1)); }

if [[ -d .agent/skills ]]; then
  for skill_dir in .agent/skills/*/; do
    name="$(basename "$skill_dir")"
    target_real="$(cd "$skill_dir" && pwd -P)"
    for side in cursor claude; do
      link=".${side}/skills/${name}"
      if [[ ! -L "$link" ]]; then
        fail "$link missing symlink to .agent/skills/${name}"
        continue
      fi
      link_real="$(cd "$link" && pwd -P)"
      [[ "$link_real" == "$target_real" ]] || fail "$link resolves to $link_real, expected $target_real"
    done
  done
fi

for kind in commands agents; do
  [[ -d .claude/${kind} ]] || continue
  for f in .claude/${kind}/*.md; do
    [[ -e "$f" ]] || continue
    name="$(basename "$f")"
    [[ -f ".cursor/${kind}/${name}" ]] || fail ".claude/${kind}/${name} has no .cursor/${kind}/${name}"
    [[ -f ".opencode/${kind}/${name}" ]] || fail ".claude/${kind}/${name} has no .opencode/${kind}/${name}"
  done
done

if [[ ! -L .cursor/mcp.json ]]; then
  fail ".cursor/mcp.json must symlink to ../.mcp.json"
fi

# Cursor hook enforcement parity
if [[ ! -f .cursor/hooks.json ]]; then
  fail ".cursor/hooks.json missing"
fi
if [[ ! -L .cursor/hooks ]]; then
  fail ".cursor/hooks must symlink to ../.claude/hooks"
else
  cursor_hooks_real="$(cd .cursor/hooks && pwd -P)"
  claude_hooks_real="$(cd .claude/hooks && pwd -P)"
  [[ "$cursor_hooks_real" == "$claude_hooks_real" ]] || fail ".cursor/hooks resolves to $cursor_hooks_real, expected $claude_hooks_real"
fi

[[ -f opencode.json ]] || fail "opencode.json missing"
jq -e '.mcp.context7 and .mcp.markitdown and .mcp.playwright and .mcp.postgres' opencode.json >/dev/null 2>&1 \
  || fail "opencode.json mcp must define context7, markitdown, playwright, postgres"

[[ -f .opencode/plugins/ka-ai-tooling.ts ]] || fail ".opencode/plugins/ka-ai-tooling.ts missing"

# Every hook registered in settings.json must exist and be executable
if [[ -f .claude/settings.json ]]; then
  while IFS= read -r hook; do
    hook_path="${hook//\$\{CLAUDE_PROJECT_DIR\}/$ROOT}"
    [[ -x "$hook_path" ]] || fail "hook not executable or missing: $hook"
  done < <(jq -r '.. | .command? // empty' .claude/settings.json)
else
  fail ".claude/settings.json missing"
fi

# Every rule referenced from opencode.json instructions must exist
while IFS= read -r inst; do
  [[ -e "$inst" ]] || fail "opencode.json instruction missing: $inst"
done < <(jq -r '.instructions[]?' opencode.json 2>/dev/null)

# Rules index lists every rule file
for r in .cursor/rules/*.mdc; do
  grep -q "$(basename "$r")" .cursor/rules/README.md || fail "$(basename "$r") not listed in .cursor/rules/README.md"
done

# Skills index lists every skill
for d in .agent/skills/*/; do
  grep -q "$(basename "$d")" .agent/skills/README.md || fail "skill $(basename "$d") not listed in .agent/skills/README.md"
done

if [[ -d .claude/commands ]]; then
  for f in .claude/commands/*.md; do
    [[ -e "$f" ]] || continue
    name="$(basename "$f")"
    [[ -e ".opencode/commands/${name}" ]] || fail ".opencode/commands/${name} missing"
  done
fi

[[ "$VIOLATIONS" -gt 0 ]] && { echo "$VIOLATIONS violation(s)"; exit 1; }
echo "OK — Cursor, Claude, and OpenCode AI tooling are in sync."
