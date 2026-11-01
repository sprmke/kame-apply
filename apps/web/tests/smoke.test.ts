import { describe, expect, it } from "vitest";
import en from "../i18n/locales/en.json";

describe("web smoke", () => {
  it("ships the app name in the default locale", () => {
    expect(en.app.name).toBe("Kame Apply");
  });
});
