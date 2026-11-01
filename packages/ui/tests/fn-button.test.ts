import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { FnButton } from "../src";

describe("FnButton", () => {
  it("renders its slot and defaults to the quiet tone", () => {
    const w = mount(FnButton, { slots: { default: "Save" } });
    expect(w.text()).toBe("Save");
    expect(w.classes()).toContain("bg-paper-1");
  });

  it("uses the persimmon fill for the primary tone", () => {
    const w = mount(FnButton, { props: { tone: "primary" }, slots: { default: "Apply" } });
    expect(w.classes()).toContain("bg-persimmon-500");
  });
});
