import { describe, expect, it } from "vitest";
import { isPublicPath } from "../app/lib/public-routes";

describe("public routes", () => {
  it("lets signed-out visitors read the legal pages", () => {
    // Google OAuth review and app stores need a public privacy policy and deletion page.
    expect(isPublicPath("/legal/privacy")).toBe(true);
    expect(isPublicPath("/legal/terms")).toBe(true);
    expect(isPublicPath("/legal/data-deletion")).toBe(true);
    expect(isPublicPath("/legal/extension-privacy")).toBe(true);
    expect(isPublicPath("/legal/privacy/")).toBe(true);
  });

  it("keeps auth and invite pages public", () => {
    for (const p of [
      "/login",
      "/register",
      "/verify-email",
      "/forgot-password",
      "/reset-password",
      "/auth/callback",
      "/invite",
    ]) {
      expect(isPublicPath(p)).toBe(true);
    }
  });

  it("does not make app pages public", () => {
    expect(isPublicPath("/")).toBe(false);
    expect(isPublicPath("/jobs")).toBe(false);
    expect(isPublicPath("/settings/ai")).toBe(false);
    expect(isPublicPath("/legally")).toBe(false);
    expect(isPublicPath("/legalish/privacy")).toBe(false);
  });
});
