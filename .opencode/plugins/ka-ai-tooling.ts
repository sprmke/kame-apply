/**
 * Kame Apply AI tooling parity for OpenCode.
 *
 * OpenCode V2 requires a default export with `{ id, setup }` (or `effect`).
 * The V1 function export is kept as `server` for older clients.
 *
 * Reuses the same shell hooks as Claude Code / Cursor:
 *   - session context (superpowers opt-in, AI tooling sync, workflow in-progress)
 *   - prod-deploy + dangerous bash guards (applywave unlock via shared lib)
 *   - shipped-migration edit block
 *   - prettier format + wrong-stack term warning after edits
 *
 * Hook scripts live under `.claude/hooks/` and share logic with Cursor via
 * `scripts/dev/prod-deploy-guard-lib.sh`.
 */

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

type PluginInput = {
  directory: string;
  worktree?: string;
  $: (
    strings: TemplateStringsArray,
    ...values: unknown[]
  ) => {
    quiet: () => {
      text: () => Promise<string>;
      nothrow: () => {
        text: () => Promise<string>;
        exitCode: Promise<number | null>;
      };
    };
  };
  client?: {
    app?: {
      log?: (args: {
        body: {
          service: string;
          level: "debug" | "info" | "warn" | "error";
          message: string;
          extra?: Record<string, unknown>;
        };
      }) => Promise<void>;
    };
  };
};

type BeforeOutput = { args: Record<string, unknown> };
type AfterOutput = {
  title: string;
  output: string;
  metadata: Record<string, unknown>;
};

type V2SetupContext = {
  location?: { directory?: string };
  session?: {
    hook: (
      name: string,
      callback: (event: Record<string, unknown>) => void | Promise<void>,
    ) => Promise<unknown>;
  };
  tool?: {
    hook: (
      name: string,
      callback: (event: Record<string, unknown>) => void | Promise<void>,
    ) => Promise<unknown>;
  };
};

function runHookScript(
  root: string,
  scriptRel: string,
  stdin: string,
): { stdout: string; status: number | null } {
  const script = path.join(root, scriptRel);
  if (!fs.existsSync(script)) {
    return { stdout: "{}", status: 1 };
  }
  const result = spawnSync("bash", [script], {
    cwd: root,
    input: stdin,
    encoding: "utf8",
    env: process.env,
    maxBuffer: 2 * 1024 * 1024,
  });
  return {
    stdout: (result.stdout || "").trim() || "{}",
    status: result.status,
  };
}

function parseHookJson(stdout: string): Record<string, unknown> {
  try {
    return JSON.parse(stdout) as Record<string, unknown>;
  } catch {
    return {};
  }
}

function permissionFromHook(parsed: Record<string, unknown>): {
  decision?: string;
  reason?: string;
  additionalContext?: string;
} {
  const specific = parsed.hookSpecificOutput as
    | Record<string, unknown>
    | undefined;
  if (specific) {
    return {
      decision: specific.permissionDecision as string | undefined,
      reason: specific.permissionDecisionReason as string | undefined,
      additionalContext: specific.additionalContext as string | undefined,
    };
  }
  return {
    additionalContext: parsed.additional_context as string | undefined,
  };
}

function resolveFilePath(args: Record<string, unknown>): string {
  const candidates = [
    args.filePath,
    args.file_path,
    args.path,
    args.file,
    args.target,
  ];
  for (const c of candidates) {
    if (typeof c === "string" && c.length > 0) return c;
  }
  return "";
}

function resolveCommand(args: Record<string, unknown>): string {
  if (typeof args.command === "string") return args.command;
  if (typeof args.cmd === "string") return args.cmd;
  if (Array.isArray(args.command)) return args.command.map(String).join(" ");
  return "";
}

function asArgs(value: unknown): Record<string, unknown> {
  return value && typeof value === "object"
    ? (value as Record<string, unknown>)
    : {};
}

function collectSessionContext(root: string): string {
  const chunks: string[] = [];

  chunks.push(
    [
      "SUPERPOWERS OPT-IN (this repo)",
      "",
      "Superpowers auto-workflows are OFF unless the user runs /superpowers-* or explicitly asks.",
      "",
      "Do NOT auto-invoke superpowers:brainstorming, writing-plans, executing-plans, etc.",
      "",
      "When Superpowers IS allowed:",
      "- Plans → docs/workflow/planned/<slug>.md (no YYYY-MM-DD- prefix)",
      "- Specs → docs/workflow/intake/<slug>-design.md",
      "- Read .agent/skills/superpowers/SKILL.md for path overrides.",
      "",
      "Retired folders (must not exist): docs/superpowers/, docs/planning/, docs/todos/. GitHub backlog is in docs/README.md.",
    ].join("\n"),
  );

  const sync = spawnSync(
    "bash",
    [path.join(root, "scripts/dev/check-ai-tooling-sync.sh")],
    {
      cwd: root,
      encoding: "utf8",
      env: process.env,
    },
  );
  if (sync.status === 0) {
    chunks.push(
      "AI tooling sync: OK (Cursor/Claude/OpenCode skills, commands, agents, hooks, mcp in sync).",
    );
  } else {
    chunks.push(
      "AI tooling sync: DRIFT DETECTED. Run 'pnpm run check:ai-tooling-sync' for details.",
    );
  }

  const progressDir = path.join(root, "docs/workflow/in-progress");
  try {
    const files = fs
      .readdirSync(progressDir)
      .filter((f) => f.endsWith(".md"))
      .sort();
    if (files.length === 0) {
      chunks.push(
        "Workflow in-progress: (none). Use /workflow-start when picking up a planned item.",
      );
    } else {
      chunks.push(
        `Workflow in-progress: ${files.join(", ")}. Primary session docs under docs/workflow/in-progress/.`,
      );
    }
  } catch {
    chunks.push(
      "Workflow in-progress: (none). Use /workflow-start when picking up a planned item.",
    );
  }

  chunks.push(
    [
      "DOCS SYNC (mandatory): Material code/behavior changes must update matching docs in the SAME change, not later.",
      "Route/page UX → docs/guides/routes/* (route-guides skill).",
      "API/env/architecture → docs/PROJECT.md.",
      "Plans/tiers → docs/architecture/plans-feature-matrix.md + Plans guides.",
      "New host capabilities → decide Plans + Team RBAC (or N/A) via plans-and-permissions skill.",
      "Tenancy/PII/site-access invariants → .cursor/rules/workspace-scoping.mdc, pii-guard.mdc, job-site-access.mdc.",
      "Invoke documentation-maintenance skill before claiming done.",
      "Canonical: CLAUDE.md § Docs are the source of truth · .cursor/rules/documentation-maintenance.mdc.",
    ].join(" "),
  );

  chunks.push(
    [
      "OpenCode project tooling (this repo)",
      "",
      "- Rules: CLAUDE.md (auto) + always-on `.cursor/rules/*.mdc` via opencode.json instructions",
      "- Skills: `.agent/skills/` (+ Claude-compat `.claude/skills/`)",
      "- Commands: `.opencode/commands/` → `.claude/commands/`",
      "- Agents: `.opencode/agents/`",
      "- MCP: opencode.json (mirrors root `.mcp.json`)",
      "- Hooks: this plugin (shared scripts under `.claude/hooks/`)",
      "- Setup: `pnpm run setup:ai-tooling` · drift: `pnpm run check:ai-tooling-sync`",
    ].join("\n"),
  );

  return chunks.join("\n\n");
}

function guardShell(root: string, command: string): void {
  if (!command) return;
  const { stdout } = runHookScript(
    root,
    ".claude/hooks/guard-shell.sh",
    JSON.stringify({ tool_input: { command } }),
  );
  const { decision, reason } = permissionFromHook(parseHookJson(stdout));
  if (decision === "deny") {
    throw new Error(
      reason ||
        "Blocked by the Kame Apply shell guard (production deploys need the unlock word applywave).",
    );
  }
  if (decision === "ask") {
    throw new Error(
      `${reason || "This command requires confirmation."} Re-run only if the user explicitly confirmed.`,
    );
  }
}

function guardEdit(root: string, filePath: string): void {
  if (!filePath) return;
  const { stdout } = runHookScript(
    root,
    ".claude/hooks/guard-shipped-migrations.sh",
    JSON.stringify({ tool_input: { file_path: filePath } }),
  );
  const { decision, reason } = permissionFromHook(parseHookJson(stdout));
  if (decision === "deny") {
    throw new Error(
      reason ||
        "Editing shipped migrations under apps/api/migrations/versions/ is not allowed. Add a new migration file.",
    );
  }
}

function annotateEditOutput(root: string, filePath: string): string[] {
  if (!filePath) return [];
  const notes: string[] = [];

  runHookScript(
    root,
    ".claude/hooks/format-edited-file.sh",
    JSON.stringify({ tool_input: { file_path: filePath } }),
  );

  const stack = runHookScript(
    root,
    ".claude/hooks/check-stack-terminology.sh",
    JSON.stringify({ tool_input: { file_path: filePath } }),
  );
  const { additionalContext: stackCtx } = permissionFromHook(
    parseHookJson(stack.stdout),
  );
  if (stackCtx) notes.push(stackCtx);

  const docs = runHookScript(
    root,
    ".claude/hooks/remind-docs-on-code-edit.sh",
    JSON.stringify({ tool_input: { file_path: filePath } }),
  );
  const { additionalContext: docsCtx } = permissionFromHook(
    parseHookJson(docs.stdout),
  );
  if (docsCtx) notes.push(docsCtx);

  return notes;
}

function appendNotesToResult(
  result: unknown,
  notes: string[],
): unknown {
  if (notes.length === 0) return result;
  const suffix = notes.map((n) => `[${n}]`).join("\n");
  if (typeof result === "string") return `${result}\n\n${suffix}`;
  if (result && typeof result === "object") {
    const record = result as Record<string, unknown>;
    if (typeof record.content === "string") {
      return { ...record, content: `${record.content}\n\n${suffix}` };
    }
    if (typeof record.output === "string") {
      return { ...record, output: `${record.output}\n\n${suffix}` };
    }
  }
  return result;
}

async function KaAiToolingServer(ctx: PluginInput) {
  const root = ctx.directory;
  const sessionContext = collectSessionContext(root);
  let injectedSession = false;

  return {
    "experimental.chat.system.transform": async (
      _input: unknown,
      output: { system: string[] },
    ) => {
      if (!injectedSession && sessionContext) {
        output.system.push(sessionContext);
        injectedSession = true;
      }
    },

    "tool.execute.before": async (
      input: { tool: string; sessionID: string; callID: string },
      output: BeforeOutput,
    ) => {
      const tool = (input.tool || "").toLowerCase();

      if (tool === "bash" || tool === "shell") {
        guardShell(root, resolveCommand(output.args));
        return;
      }

      if (
        tool === "edit" ||
        tool === "write" ||
        tool === "strreplace" ||
        tool === "apply_patch"
      ) {
        guardEdit(root, resolveFilePath(output.args));
      }
    },

    "tool.execute.after": async (
      input: {
        tool: string;
        sessionID: string;
        callID: string;
        args: Record<string, unknown>;
      },
      output: AfterOutput,
    ) => {
      const tool = (input.tool || "").toLowerCase();
      if (
        tool !== "edit" &&
        tool !== "write" &&
        tool !== "strreplace" &&
        tool !== "apply_patch"
      ) {
        return;
      }

      const notes = annotateEditOutput(
        root,
        resolveFilePath(input.args || {}),
      );
      if (notes.length > 0) {
        output.output = `${output.output || ""}\n\n${notes
          .map((n) => `[${n}]`)
          .join("\n")}`;
      }
    },
  };
}

async function setupKaAiTooling(ctx: V2SetupContext) {
  const root = ctx.location?.directory;
  if (!root) return;

  const sessionContext = collectSessionContext(root);
  let injectedSession = false;

  if (ctx.session?.hook) {
    await ctx.session.hook("context", (event) => {
      if (injectedSession || !sessionContext) return;
      const system = event.system;
      if (Array.isArray(system)) {
        system.push({ type: "text", text: sessionContext });
        injectedSession = true;
      }
    });
  }

  if (!ctx.tool?.hook) return;

  await ctx.tool.hook("execute.before", (event) => {
    const tool = String(event.tool || "").toLowerCase();
    const input = asArgs(event.input);

    if (tool === "bash" || tool === "shell") {
      guardShell(root, resolveCommand(input));
      return;
    }

    if (
      tool === "edit" ||
      tool === "write" ||
      tool === "strreplace" ||
      tool === "apply_patch"
    ) {
      guardEdit(root, resolveFilePath(input));
    }
  });

  await ctx.tool.hook("execute.after", (event) => {
    if (event.status !== "completed") return;
    const tool = String(event.tool || "").toLowerCase();
    if (
      tool !== "edit" &&
      tool !== "write" &&
      tool !== "strreplace" &&
      tool !== "apply_patch"
    ) {
      return;
    }

    const notes = annotateEditOutput(root, resolveFilePath(asArgs(event.input)));
    if (notes.length === 0) return;
    event.result = appendNotesToResult(event.result, notes);
  });
}

export default {
  id: "kame-apply-ai-tooling",
  server: KaAiToolingServer,
  setup: setupKaAiTooling,
};
