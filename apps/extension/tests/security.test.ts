import { describe, expect, it } from "vitest";
import { isAllowedApiBase, looksLikeExtensionToken } from "../utils/api";
import { isSensitiveField } from "../utils/extract";

describe("extension connect trust", () => {
  it("only accepts our own API origins", () => {
    expect(isAllowedApiBase("http://localhost:8100")).toBe(true);
    expect(isAllowedApiBase("https://api.kame.apply")).toBe(true);
    expect(isAllowedApiBase("https://app.kame.apply")).toBe(true);
    expect(isAllowedApiBase("https://attacker.tld")).toBe(false);
    expect(isAllowedApiBase("https://kame.apply.evil.tld")).toBe(false);
    expect(isAllowedApiBase("javascript:alert(1)")).toBe(false);
    expect(isAllowedApiBase("")).toBe(false);
  });

  it("only accepts extension tokens", () => {
    expect(looksLikeExtensionToken("ka_ext_abc")).toBe(true);
    expect(looksLikeExtensionToken("ka_run_abc")).toBe(false);
    expect(looksLikeExtensionToken("")).toBe(false);
  });
});

describe("sensitive field detection", () => {
  const make = (attrs: Record<string, string>) => {
    const el = document.createElement("input");
    for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
    return el;
  };

  it("treats government ids, bank, and card fields as sensitive", () => {
    expect(isSensitiveField(make({ name: "ssn" }), "Social Security Number")).toBe(true);
    expect(isSensitiveField(make({ name: "account_number" }), "Account number")).toBe(true);
    expect(isSensitiveField(make({ autocomplete: "cc-number" }), "Card")).toBe(true);
    expect(isSensitiveField(make({ name: "dob" }), "Date of birth")).toBe(true);
    expect(isSensitiveField(make({ type: "password" }), "Password")).toBe(true);
  });

  it("leaves ordinary contact fields alone", () => {
    expect(isSensitiveField(make({ name: "email" }), "Email")).toBe(false);
    expect(isSensitiveField(make({ name: "phone" }), "Phone")).toBe(false);
    expect(isSensitiveField(make({ name: "linkedin" }), "LinkedIn URL")).toBe(false);
  });
});
