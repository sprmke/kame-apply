import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { FnSuggestions } from "../src";
import { EMPTY_OPTION, fromItemValue, toItemValue } from "../src/select-value";

describe("FnSuggestions", () => {
  it("renders one button per option and emits the chosen answer", async () => {
    const w = mount(FnSuggestions, {
      props: { options: ["Immediately", "2 weeks", "30 days"], label: "Common answers" },
    });
    const buttons = w.findAll("button");
    expect(buttons.map((b) => b.text())).toEqual(["Immediately", "2 weeks", "30 days"]);
    await buttons[2]!.trigger("click");
    expect(w.emitted("select")).toEqual([["30 days"]]);
  });

  it("names the group for assistive tech and keeps a 44px target", () => {
    const w = mount(FnSuggestions, { props: { options: ["Yes"], label: "Common answers" } });
    expect(w.attributes("role")).toBe("group");
    expect(w.attributes("aria-label")).toBe("Common answers");
    expect(w.find("button").classes()).toContain("min-h-11");
  });

  it("renders nothing without options", () => {
    const w = mount(FnSuggestions, { props: { options: [], label: "Common answers" } });
    expect(w.find("button").exists()).toBe(false);
  });
});

describe("select empty option", () => {
  it("swaps the empty value for a sentinel Reka UI accepts", () => {
    expect(toItemValue("")).toBe(EMPTY_OPTION);
    expect(toItemValue("remote")).toBe("remote");
    expect(fromItemValue(EMPTY_OPTION)).toBe("");
    expect(fromItemValue("remote")).toBe("remote");
  });
});
