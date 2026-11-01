import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import en from "../i18n/locales/en.json";

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? files(p) : /\.(vue|ts)$/.test(f) ? [p] : [];
  });
}

function files2(dir: string): string[] {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    if (f === "__pycache__") return [];
    return statSync(p).isDirectory() ? files2(p) : f.endsWith(".py") ? [p] : [];
  });
}

const lookup = (key: string) =>
  key.split(".").reduce<unknown>((o, k) => (o as Record<string, unknown> | undefined)?.[k], en);
const src = files(join(__dirname, "../app"))
  .map((p) => readFileSync(p, "utf8"))
  .join("\n");

describe("message catalog", () => {
  it("defines every static key used in the app", () => {
    const keys = [...src.matchAll(/\b\$?t\(\s*["']([a-zA-Z0-9_.]+)["']/g)].map((m) => m[1]!);
    const missing = [...new Set(keys)].filter((k) => typeof lookup(k) !== "string");
    expect(missing).toEqual([]);
  });

  it("covers every dynamic key family", () => {
    const families: Record<string, string[]> = {
      nav: [
        "today",
        "tracks",
        "jobs",
        "applications",
        "responses",
        "runs",
        "studio",
        "answers",
        "coach",
        "contacts",
        "safety",
        "settings",
      ],
      role: ["owner", "admin", "member", "viewer"],
      theme: ["system", "light", "dark"],
      "ai.status": ["valid", "invalid", "untested"].map((s) => s),
    };
    for (const [family, names] of Object.entries(families)) {
      for (const n of names) {
        const key = family === "ai.status" ? `ai.status_${n}` : `${family}.${n}`;
        expect(lookup(key), key).toBeTypeOf("string");
      }
    }
    for (const tier of ["bulk", "standard", "premium"])
      expect(lookup(`ai.tier_${tier}`)).toBeTypeOf("string");
    for (const a of ["leave", "transfer", "delete"]) {
      expect(lookup(`danger.${a}`)).toBeTypeOf("string");
      expect(lookup(`danger.${a}Title`)).toBeTypeOf("string");
    }
    for (const s of ["ai", "profile", "track", "extension", "done", "todo", "soon"])
      expect(lookup(`onboarding.${s}`)).toBeTypeOf("string");
  });

  it("has a message for every error code the API can return", () => {
    const api = files2(join(__dirname, "../../api/app"))
      .map((p) => readFileSync(p, "utf8"))
      .join("\n");
    const codes = new Set(
      [...api.matchAll(/(?:AppError|OAuthError)\(\s*["']([a-z_]+)["']/g)].map((m) => m[1]!),
    );
    expect(codes.size).toBeGreaterThan(20);
    const missing = [...codes].filter((c) => typeof lookup(`errors.${c}`) !== "string");
    expect(missing).toEqual([]);
  });

  it("uses no em dashes and no exclamation marks in copy", () => {
    const text = JSON.stringify(en);
    expect(text).not.toMatch(/—/);
    expect(text).not.toMatch(/!/);
  });
});
