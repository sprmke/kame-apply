"""CLI: login to Kame, work via local `claude -p`, schedule helpers.

# ruff: noqa: S603,S607

Never reads or stores Claude credentials. Only talks to Kame Apply OAuth/MCP
and shells out to the user's installed `claude` binary.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import typer

app = typer.Typer(add_completion=False, no_args_is_help=True)
CONFIG = Path.home() / ".config" / "kame-agent" / "config.json"


def _load() -> dict:
    if CONFIG.exists():
        return json.loads(CONFIG.read_text())
    return {}


def _save(data: dict) -> None:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(data, indent=2))


@app.command()
def login(
    api: str = typer.Option("http://localhost:8100", help="Kame API base URL"),
    token: str = typer.Option("", help="Personal access token from Settings → Integrations"),
) -> None:
    """Store a Kame PAT (not a Claude token) for local status/pull helpers."""
    if not token:
        typer.echo("Create a PAT in Settings → Integrations, then: kame-agent login --token <pat>")
        raise typer.Exit(1)
    if "CLAUDE" in token.upper() or token.startswith("sk-ant"):
        typer.echo("Refusing Claude/Anthropic credentials. Use a Kame Apply PAT only.")
        raise typer.Exit(2)
    _save({"api_base": api.rstrip("/"), "pat": token})
    typer.echo("Saved Kame PAT to ~/.config/kame-agent/config.json")


@app.command()
def work(max_tasks: int = typer.Option(5, "--max")) -> None:
    """Run the user's installed `claude -p` against the agent inbox."""
    claude = shutil.which("claude")
    if not claude:
        typer.echo("claude binary not found on PATH")
        raise typer.Exit(1)
    # Never --bare; never inject Claude OAuth env tokens.
    _banned = "_".join(("CLAUDE", "CODE", "OAUTH", "TOKEN"))
    env = {k: v for k, v in os.environ.items() if k != _banned}
    cmd = [
        claude,
        "-p",
        f"/kame:work --max {max_tasks}",
        "--mcp-config",
        str(Path.home() / ".claude.json"),
        "--allowedTools",
        "mcp__kame__*",
        "--permission-mode",
        "dontAsk",
        "--output-format",
        "stream-json",
    ]
    raise typer.Exit(subprocess.call(cmd, env=env))


@app.command("schedule")
def schedule(
    action: str = typer.Argument(..., help="install|remove"),
    every: str = typer.Option("2h", "--every"),
) -> None:
    """Install or remove a user-owned launchd/cron job that runs `kame-agent work`."""
    label = "app.kame.agent.work"
    if sys.platform == "darwin":
        plist = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
        if action == "remove":
            subprocess.call(["launchctl", "unload", str(plist)])
            if plist.exists():
                plist.unlink()
            typer.echo("Removed launchd job")
            return
        if action != "install":
            raise typer.Exit(1)
        interval = 7200
        if every.endswith("h"):
            interval = int(every[:-1]) * 3600
        elif every.endswith("m"):
            interval = int(every[:-1]) * 60
        exe = shutil.which("kame-agent") or "kame-agent"
        plist.write_text(
            f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>{label}</string>
  <key>ProgramArguments</key><array><string>{exe}</string><string>work</string></array>
  <key>StartInterval</key><integer>{interval}</integer>
  <key>RunAtLoad</key><true/>
</dict></plist>
"""
        )
        subprocess.call(["launchctl", "load", str(plist)])
        typer.echo(f"Installed launchd job every {every}")
        return
    # cron fallback
    if action == "install":
        typer.echo(f"Add a cron entry for: kame-agent work  (every {every})")
    else:
        typer.echo("Remove the cron entry that runs kame-agent work")


@app.command()
def status() -> None:
    cfg = _load()
    typer.echo(
        json.dumps({"config": {k: ("***" if k == "pat" else v) for k, v in cfg.items()}}, indent=2)
    )


@app.command()
def pull(track: str = typer.Argument("default")) -> None:
    typer.echo(
        f"pull {track}: use MCP tools from Claude Code for now; folder sync lands with Phase 15."
    )


@app.command()
def push() -> None:
    typer.echo("push: proposals only; use MCP propose_* tools. Folder sync lands with Phase 15.")


if __name__ == "__main__":
    app()
