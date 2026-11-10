#!/usr/bin/env bash
# One-shot post-clone AI tooling setup for Kame Apply.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

info() { printf '→ %s\n' "$*"; }
ok() { printf '✓ %s\n' "$*"; }
warn() { printf '⚠ %s\n' "$*" >&2; }

link_relative() {
  local link="$1" target="$2"
  mkdir -p "$(dirname "$link")"
  if [[ -L "$link" ]]; then
    [[ "$(readlink "$link")" == "$target" ]] && return 0
    rm "$link"
  elif [[ -e "$link" ]]; then
    echo "ERROR: $link exists and is not a symlink"
    exit 1
  fi
  ln -s "$target" "$link"
  ok "Linked $link -> $target"
}

info "MCP config"
[[ -f .mcp.json ]] || { echo "ERROR: .mcp.json missing"; exit 1; }
link_relative ".cursor/mcp.json" "../.mcp.json"

info "Team skills (.agent/skills symlinks)"
[[ -d .agent/skills ]] || { echo "ERROR: .agent/skills missing"; exit 1; }
for skill_dir in .agent/skills/*/; do
  [[ -d "$skill_dir" ]] || continue
  name="$(basename "$skill_dir")"
  for side in cursor claude; do
    link=".${side}/skills/${name}"
    link_relative "$link" "../../.agent/skills/${name}"
  done
done

info "OpenCode command symlinks"
mkdir -p .opencode/commands .opencode/agents .opencode/plugins
for cmd in .claude/commands/*.md; do
  [[ -e "$cmd" ]] || continue
  name="$(basename "$cmd")"
  link_relative ".opencode/commands/${name}" "../../.claude/commands/${name}"
done

for agent_file in .claude/agents/*.md; do
  [[ -e "$agent_file" ]] || continue
  name="$(basename "$agent_file")"
  link_relative ".cursor/agents/${name}" "../../.claude/agents/${name}"
  link_relative ".opencode/agents/${name}" "../../.claude/agents/${name}"
done

for cmd in .claude/commands/*.md; do
  [[ -e "$cmd" ]] || continue
  name="$(basename "$cmd")"
  link_relative ".cursor/commands/${name}" "../../.claude/commands/${name}" || true
done

chmod +x .claude/hooks/*.sh scripts/dev/*.sh 2>/dev/null || true

info "Required CLIs"
for tool in jq git node pnpm uv docker; do
  command -v "$tool" >/dev/null 2>&1 && ok "$tool" || warn "$tool not found (needed from Phase 1; jq/git needed now)"
done
command -v python3.13 >/dev/null 2>&1 && ok "python3.13" || warn "python 3.13 not on PATH (uv can install it: uv python install 3.13)"

info "Optional tools"
command -v markitdown-mcp >/dev/null 2>&1 && ok "markitdown-mcp on PATH" || warn "markitdown-mcp not on PATH — uv tool install markitdown-mcp"

# Codex skill, command, agent and hook compatibility
python3 "$ROOT/.codex/sync.py"

bash "$ROOT/scripts/dev/check-ai-tooling-sync.sh"
ok "AI tooling setup complete — re-run: pnpm run setup:ai-tooling"
