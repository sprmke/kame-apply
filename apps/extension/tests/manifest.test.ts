import { execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { beforeAll, describe, expect, it } from "vitest";

// Builds first so the check never silently skips on a fresh clone (~0.5 s).
describe("built manifest", () => {
  let m: Record<string, unknown> & {
    permissions?: string[];
    host_permissions?: string[];
    side_panel?: { default_path?: string };
  };

  beforeAll(() => {
    execSync("pnpm exec wxt build", { stdio: "pipe" });
    m = JSON.parse(readFileSync(".output/chrome-mv3/manifest.json", "utf8"));
  }, 60_000);

  it("is MV3 with a side panel", () => {
    expect(m.manifest_version).toBe(3);
    expect(m.side_panel?.default_path).toBeTruthy();
  });

  it("requests no required broad host permissions or the tabs permission", () => {
    expect(m.host_permissions ?? []).not.toContain("<all_urls>");
    expect(m.permissions ?? []).not.toContain("tabs");
    // Host access is optional and requested per site at use time.
    expect(Array.isArray(m.optional_host_permissions)).toBe(true);
  });
});
