#!/usr/bin/env python3
"""Wire and verify the cross-provider agent stack for this repo.

Providers: Codex, Cursor, Claude Code, OpenCode.
Canonical sources:
  AGENTS.md                  project instructions every provider reads
  CLAUDE.md                  thin Claude adapter that imports AGENTS.md
  .cursor/rules/*.mdc        always-on and glob-scoped constraints
  .agent/skills/<name>/      project skills
  .claude/{commands,agents}  slash commands and specialist agents
  .claude/hooks + .cursor/hooks
  .mcp.json                  MCP servers
Derived:
  .cursor/{skills,commands,agents,mcp.json}, .claude/skills,
  .opencode/{commands,agents}, .agents/skills, .codex/*

Usage:
  python3 scripts/dev/ai-tooling.py wire    # idempotent: link, generate, then check
  python3 scripts/dev/ai-tooling.py check   # exit 1 on drift
  python3 scripts/dev/ai-tooling.py status  # what each provider sees

Config: .ai-tooling.json at the repo root (optional; sane defaults when absent).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / ".ai-tooling.json"

DEFAULTS = {
    "name": ROOT.name,
    "unlockWord": "deskwave",
    "migrations": [],
    "codePaths": ["src", "app", "apps", "packages"],
    "docsPath": "docs",
    "banned": [],
    "opencode": {
        "skillRoots": [".agent/skills", ".agents/skills"],
        "requiredMcp": [],
        "denyMigrations": True,
        "askOnForcePush": True,
        "allowExternalLibrary": True,
    },
}

# ---------------------------------------------------------------- helpers


def load_config() -> dict:
    cfg = json.loads(json.dumps(DEFAULTS))  # deep copy
    if CONFIG_PATH.is_file():
        user = json.loads(CONFIG_PATH.read_text())
        for key, value in user.items():
            if isinstance(value, dict) and isinstance(cfg.get(key), dict):
                cfg[key].update(value)
            else:
                cfg[key] = value
    return cfg


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def ok(msg: str) -> None:
    print(f"  ok    {msg}")


def info(msg: str) -> None:
    print(f"  ..    {msg}")


def warn(msg: str) -> None:
    print(f"  warn  {msg}", file=sys.stderr)


def fail(msg: str) -> None:
    print(f"  FAIL  {msg}", file=sys.stderr)


def link_relative(link: Path, target: str) -> bool:
    """Create a relative symlink. Never clobbers a real file or directory."""
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink():
        if os.readlink(link) == target:
            return False
        link.unlink()
    elif link.exists():
        warn(f"{rel(link)} exists and is not a symlink; leaving it alone")
        return False
    link.symlink_to(target, target_is_directory=True)
    ok(f"linked {rel(link)} -> {target}")
    return True


def skill_dirs(base: Path) -> list[Path]:
    if not base.is_dir():
        return []
    return sorted(
        p for p in base.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()
    )


def frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "", text
    return parts[1], parts[2].lstrip("\n")


def scalar(header: str, field: str, default: str = "") -> str:
    match = re.search(r"^" + re.escape(field) + r":\s*(.+)$", header, re.M)
    if not match:
        return default
    value = match.group(1).strip()
    if value in ("|", ">", ">-", "|-"):
        return default
    return value.strip("\"'")


def yaml_list(header: str, field: str) -> list[str]:
    """Read a flow list (`[a, b]`) or a block list (`- a`) from frontmatter."""
    flow = re.search(r"^" + re.escape(field) + r":\s*\[(.*)\]\s*$", header, re.M)
    if flow:
        return [x.strip().strip("\"'") for x in flow.group(1).split(",") if x.strip()]
    block = re.search(
        r"^" + re.escape(field) + r":\s*\n((?:[ \t]*-[ \t]*.+\n?)+)", header, re.M
    )
    if block:
        return [
            m.group(1).strip().strip("\"'")
            for m in re.finditer(r"-[ \t]*(.+)", block.group(1))
        ]
    single = scalar(header, field)
    return [single] if single else []


# ---------------------------------------------------------------- wire


def wire_mcp() -> None:
    mcp = ROOT / ".mcp.json"
    if not mcp.is_file():
        info("no .mcp.json; skipping Cursor MCP symlink")
        return
    link_relative(ROOT / ".cursor/mcp.json", "../.mcp.json")


def skill_roots(cfg: dict) -> list[str]:
    roots = (cfg.get("opencode") or {}).get("skillRoots") or [
        ".agent/skills",
        ".agents/skills",
    ]
    return [root for root in roots if (ROOT / root).is_dir()]


def wire_skills(cfg: dict) -> None:
    total = 0
    seen: set[str] = set()
    for base in skill_roots(cfg):
        for skill in skill_dirs(ROOT / base):
            if skill.name.startswith("source-command-") or skill.name in seen:
                continue
            seen.add(skill.name)
            total += 1
            for side in ("cursor", "claude"):
                if base == f".{side}/skills":
                    continue
                relative_base = os.path.relpath(ROOT / base, ROOT / f".{side}/skills")
                link_relative(
                    ROOT / f".{side}/skills/{skill.name}",
                    f"{relative_base}/{skill.name}",
                )
    if total == 0:
        info("no project skills yet")


def wire_commands() -> None:
    canonical = ROOT / ".claude/commands"
    if not canonical.is_dir():
        info("no .claude/commands; skipping command links")
        return
    for file in sorted(canonical.glob("*.md")):
        link_relative(
            ROOT / ".opencode/commands" / file.name,
            f"../../.claude/commands/{file.name}",
        )
        # Cursor may own the canonical file in some repos; only link when absent.
        cursor_link = ROOT / ".cursor/commands" / file.name
        if not cursor_link.exists() and not cursor_link.is_symlink():
            link_relative(cursor_link, f"../../.claude/commands/{file.name}")


OPENCODE_AGENT_DENY_EDIT = """---
description: {description}
mode: subagent
permissions:
  - action: edit
    resource: "*"
    effect: deny
  - action: subagent
    resource: "*"
    effect: deny
---

{body}
"""

OPENCODE_AGENT_ALL_TOOLS = """---
description: {description}
mode: subagent
---

{body}
"""


def wire_agents() -> None:
    canonical = ROOT / ".claude/agents"
    if not canonical.is_dir():
        info("no .claude/agents; skipping agent links")
        return
    for file in sorted(canonical.glob("*.md")):
        link_relative(
            ROOT / ".cursor/agents" / file.name, f"../../.claude/agents/{file.name}"
        )

        target = ROOT / ".opencode/agents" / file.name
        if target.exists():
            continue
        header, body = frontmatter(file.read_text())
        description = scalar(
            header, "description", f"{file.stem} specialist for this repo."
        )
        tools = yaml_list(header, "tools")
        can_edit = not tools or any(
            t.lower() in {"edit", "write", "apply_patch", "*"} for t in tools
        )
        template = OPENCODE_AGENT_ALL_TOOLS if can_edit else OPENCODE_AGENT_DENY_EDIT
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            template.format(
                description=json.dumps(description), body=body.rstrip() + "\n"
            )
        )
        ok(f"generated {rel(target)}")


def wire_hooks() -> None:
    for folder in (".claude/hooks", ".cursor/hooks"):
        directory = ROOT / folder
        if not directory.is_dir():
            continue
        for script in directory.glob("*.sh"):
            script.chmod(script.stat().st_mode | 0o111)


def wire_codex_mcp() -> None:
    """Regenerate [mcp_servers.*] in .codex/config.toml from .mcp.json."""
    source = ROOT / ".mcp.json"
    if not source.is_file():
        return
    servers = json.loads(source.read_text()).get("mcpServers") or {}
    if not servers:
        return

    lines = ["# Project Codex layer. MCP servers below mirror .mcp.json."]
    for name in sorted(servers):
        spec = servers[name]
        lines += ["", f"[mcp_servers.{name}]"]
        if spec.get("url"):
            lines.append(f"url = {json.dumps(spec['url'])}")
            continue
        lines.append(f"command = {json.dumps(spec.get('command', ''))}")
        args = spec.get("args") or []
        lines.append("args = [" + ", ".join(json.dumps(str(a)) for a in args) + "]")
        env = spec.get("env") or {}
        if env:
            inner = ", ".join(f"{k} = {json.dumps(str(v))}" for k, v in env.items())
            lines.append("env = { " + inner + " }")

    target = ROOT / ".codex/config.toml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines).strip() + "\n")
    ok(f"regenerated {rel(target)} from .mcp.json ({len(servers)} servers)")


def wire_codex() -> None:
    sync = ROOT / ".codex/sync.py"
    if not sync.is_file():
        warn(".codex/sync.py missing; Codex compatibility layer not generated")
        return
    result = subprocess.run(
        [sys.executable, str(sync)], cwd=ROOT, capture_output=True, text=True
    )
    if result.returncode == 0:
        ok(result.stdout.strip() or "codex layer regenerated")
    else:
        warn(f".codex/sync.py failed: {result.stderr.strip()[:400]}")


# ---------------------------------------------------------------- check


class Checker:
    def __init__(self) -> None:
        self.violations: list[str] = []

    def require(self, condition: bool, message: str) -> None:
        if not condition:
            self.violations.append(message)

    def report(self) -> int:
        if self.violations:
            print()
            for violation in self.violations:
                fail(violation)
            print(f"\n{len(self.violations)} violation(s).")
            return 1
        print("OK - Codex, Cursor, Claude Code, and OpenCode are in sync.")
        return 0


def check_instructions(c: Checker) -> None:
    agents = ROOT / "AGENTS.md"
    claude = ROOT / "CLAUDE.md"
    c.require(agents.is_file(), "AGENTS.md missing (canonical instructions)")
    if claude.is_file():
        text = claude.read_text()
        c.require(
            "@AGENTS.md" in text, "CLAUDE.md must import AGENTS.md with @AGENTS.md"
        )


def check_skills(c: Checker, cfg: dict) -> None:
    seen: set[str] = set()
    for base in skill_roots(cfg):
        for skill in skill_dirs(ROOT / base):
            if skill.name.startswith("source-command-") or skill.name in seen:
                continue
            seen.add(skill.name)
            for side in ("cursor", "claude"):
                if base == f".{side}/skills":
                    continue
                link = ROOT / f".{side}/skills/{skill.name}"
                # Either direction is fine (real dir or symlink) as long as both
                # providers resolve the same files. A copy that diverges fails.
                if not link.exists():
                    c.require(False, f"{rel(link)} missing for {base}/{skill.name}")
                    continue
                c.require(
                    Path(os.path.realpath(link)) == Path(os.path.realpath(skill)),
                    f"{rel(link)} resolves to a different copy than {base}/{skill.name}",
                )


def check_parity(c: Checker) -> None:
    for kind in ("commands", "agents"):
        claude = ROOT / f".claude/{kind}"
        if not claude.is_dir():
            continue
        for file in sorted(claude.glob("*.md")):
            c.require(
                (ROOT / f".cursor/{kind}/{file.name}").exists(),
                f".cursor/{kind}/{file.name} missing",
            )
            c.require(
                (ROOT / f".opencode/{kind}/{file.name}").exists(),
                f".opencode/{kind}/{file.name} missing",
            )


def hook_names(config_file: Path, folder: str) -> set[str]:
    if not config_file.is_file():
        return set()
    try:
        data = json.loads(config_file.read_text())
    except json.JSONDecodeError:
        return set()
    found = set()
    stack = [data]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            command = node.get("command")
            if isinstance(command, str):
                for match in re.finditer(rf"{folder}/([A-Za-z0-9_.-]+\.sh)", command):
                    found.add(match.group(1))
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return found


def check_hooks(c: Checker) -> None:
    cursor = hook_names(ROOT / ".cursor/hooks.json", ".cursor/hooks")
    claude = hook_names(ROOT / ".claude/settings.json", ".claude/hooks")
    for name in sorted(cursor - claude):
        c.require(
            False,
            f"hook {name} wired in .cursor/hooks.json has no .claude/settings.json counterpart",
        )
    for name in sorted(claude - cursor):
        c.require(
            False,
            f"hook {name} wired in .claude/settings.json has no .cursor/hooks.json counterpart",
        )
    # A wired hook must exist on disk. A Cursor hook may delegate to the Claude one.
    for name in sorted(cursor | claude):
        c.require(
            (ROOT / ".claude/hooks" / name).is_file(),
            f"hook {name} is wired but .claude/hooks/{name} is missing",
        )
        c.require(
            (ROOT / ".cursor/hooks" / name).is_file(),
            f"hook {name} is wired but .cursor/hooks/{name} is missing",
        )


def check_mcp(c: Checker, cfg: dict) -> None:
    mcp = ROOT / ".mcp.json"
    if not mcp.is_file():
        return
    link = ROOT / ".cursor/mcp.json"
    if not link.is_symlink():
        c.require(False, ".cursor/mcp.json must symlink to ../.mcp.json")
    else:
        c.require(
            Path(os.path.realpath(link)) == Path(os.path.realpath(mcp)),
            ".cursor/mcp.json symlink does not resolve to .mcp.json",
        )


def check_opencode(c: Checker, cfg: dict) -> None:
    config = ROOT / "opencode.json"
    if not config.is_file():
        c.require(False, "opencode.json missing")
        return
    try:
        data = json.loads(config.read_text())
    except json.JSONDecodeError as error:
        c.require(False, f"opencode.json is not valid JSON: {error}")
        return

    c.require(
        isinstance(data.get("mcp", {}).get("servers"), dict),
        "opencode.json must use V2 mcp.servers",
    )
    c.require(
        isinstance(data.get("skills"), list),
        "opencode.json skills must be an array (V2)",
    )
    c.require(
        isinstance(data.get("permissions"), list),
        "opencode.json must use the V2 permissions array",
    )
    c.require(
        bool(data.get("instructions")),
        "opencode.json instructions must list the always-on rules",
    )

    skills = data.get("skills") or []
    c.require(
        "~/.agents/skill-library" not in skills,
        "opencode.json must not expose ~/.agents/skill-library directly (159 skills become discoverable)",
    )

    servers = set((data.get("mcp", {}).get("servers") or {}).keys())
    for required in cfg["opencode"].get("requiredMcp", []):
        c.require(
            required in servers, f"opencode.json mcp.servers missing '{required}'"
        )

    if (ROOT / ".mcp.json").is_file():
        declared = set(
            json.loads((ROOT / ".mcp.json").read_text()).get("mcpServers", {}).keys()
        )
        for name in sorted(declared - servers):
            c.require(
                False,
                f"MCP server '{name}' in .mcp.json has no opencode.json mcp.servers entry",
            )

    # Migration guard must be enforced by config, not only by a hook.
    rules = data.get("permissions") or []
    denied_edit = [
        r for r in rules if r.get("action") == "edit" and r.get("effect") == "deny"
    ]
    for migration in cfg.get("migrations", []):
        c.require(
            any(migration in str(r.get("resource", "")) for r in denied_edit),
            f"opencode.json must deny edits under {migration}",
        )

    c.require(
        any(r.get("action") == "external_directory" for r in rules),
        "opencode.json should declare an external_directory policy",
    )


def check_codex(c: Checker) -> None:
    c.require((ROOT / ".codex/sync.py").is_file(), ".codex/sync.py missing")
    c.require(
        (ROOT / ".codex/compatibility.json").is_file(),
        ".codex/compatibility.json missing - run wire",
    )
    source = ROOT / ".mcp.json"
    config = ROOT / ".codex/config.toml"
    if not source.is_file():
        return
    declared = set(json.loads(source.read_text()).get("mcpServers", {}).keys())
    if not declared:
        return
    if not config.is_file():
        c.require(False, ".codex/config.toml missing but .mcp.json declares servers")
        return
    found = set(re.findall(r"^\[mcp_servers\.([A-Za-z0-9_-]+)\]", config.read_text(), re.M))
    for name in sorted(declared - found):
        c.require(False, f"MCP server '{name}' in .mcp.json has no .codex/config.toml entry")


def check_stack_terms(c: Checker, cfg: dict) -> None:
    banned = [b for b in cfg.get("banned", []) if b]
    if not banned:
        return
    hook = ROOT / ".claude/hooks/check-stack-terminology.sh"
    if not hook.is_file():
        return
    text = hook.read_text()
    # Config-driven hooks read the list from .ai-tooling.json; bespoke hooks inline it.
    if "BANNED" in text and "_repo.sh" in text:
        return
    for term in banned:
        c.require(
            term in text, f"check-stack-terminology.sh missing banned term: {term}"
        )


def cmd_check(cfg: dict) -> int:
    c = Checker()
    check_instructions(c)
    check_skills(c, cfg)
    check_parity(c)
    check_hooks(c)
    check_mcp(c, cfg)
    check_opencode(c, cfg)
    check_codex(c)
    check_stack_terms(c, cfg)
    return c.report()


# ---------------------------------------------------------------- status


def cmd_status(cfg: dict) -> int:
    rows = [
        ("AGENTS.md", (ROOT / "AGENTS.md").is_file()),
        ("CLAUDE.md", (ROOT / "CLAUDE.md").is_file()),
        (".cursor/rules", len(list((ROOT / ".cursor/rules").glob("*.mdc")))),
        (".agent/skills", len(skill_dirs(ROOT / ".agent/skills"))),
        (".claude/commands", len(list((ROOT / ".claude/commands").glob("*.md")))),
        (".claude/agents", len(list((ROOT / ".claude/agents").glob("*.md")))),
        (".opencode/agents", len(list((ROOT / ".opencode/agents").glob("*.md")))),
        (".codex/agents", len(list((ROOT / ".codex/agents").glob("*.toml")))),
        (".mcp.json", (ROOT / ".mcp.json").is_file()),
        ("opencode.json", (ROOT / "opencode.json").is_file()),
    ]
    print(f"{cfg['name']}")
    for label, value in rows:
        mark = "yes" if value is True else ("-" if value is False else str(value))
        print(f"  {label:<20} {mark}")
    print(f"\nUnlock word: {cfg['unlockWord']}")
    return 0


# ---------------------------------------------------------------- main


def cmd_wire(cfg: dict) -> int:
    print(f"Wiring {cfg['name']}")
    wire_mcp()
    wire_skills(cfg)
    wire_commands()
    wire_agents()
    wire_hooks()
    wire_codex_mcp()
    wire_codex()
    print()
    return cmd_check(cfg)


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "check"
    cfg = load_config()
    if command == "wire":
        return cmd_wire(cfg)
    if command == "check":
        return cmd_check(cfg)
    if command == "status":
        return cmd_status(cfg)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
