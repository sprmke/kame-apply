import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { beforeEach, describe, expect, it } from "vitest";
import { extractFields } from "../utils/extract";
import { applyInstructions } from "../utils/fill";

const root = dirname(fileURLToPath(import.meta.url));

describe("greenhouse fixture extract + fill", () => {
  beforeEach(() => {
    const html = readFileSync(join(root, "fixtures/greenhouse-apply.html"), "utf8");
    document.body.innerHTML = html;
  });

  it("does not overwrite a field that already has the value", () => {
    document.body.innerHTML =
      '<label for="email">Email</label><input id="email" value="a@b.com" />';
    const result = applyInstructions([{ field_id: "email", action: "fill", value: "a@b.com" }]);
    expect(result.skipped).toBe(1);
    expect(result.filled).toBe(0);
  });

  it("fills the focused field for an answer insert", () => {
    document.body.innerHTML =
      '<label for="q">Why do you want this role?</label><textarea id="q"></textarea>';
    const el = document.querySelector<HTMLTextAreaElement>("#q")!;
    el.focus();
    const result = applyInstructions([
      { field_id: "focused", action: "fill", value: "Because the work is real." },
    ]);
    expect(result.filled).toBe(1);
    expect(el.value).toBe("Because the work is real.");
  });

  it("extracts fields and fills first name", () => {
    const fields = extractFields(document);
    expect(fields.some((f) => /first/i.test(f.label))).toBe(true);
    expect(fields.some((f) => /ssn|social/i.test(f.label + f.name))).toBe(true);

    const first = fields.find((f) => /first/i.test(f.label))!;
    const result = applyInstructions([
      { field_id: first.id, action: "fill", value: "Ada", badge: "profile" },
    ]);
    expect(result.filled).toBe(1);
    const el = document.querySelector<HTMLInputElement>("#first_name");
    expect(el?.value).toBe("Ada");
  });
});
