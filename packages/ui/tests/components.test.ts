import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { nextTick, ref } from "vue";
import {
  FnButton,
  FnCheckbox,
  FnChip,
  FnDialog,
  FnField,
  FnGradeRing,
  FnInput,
  FnPencilText,
  FnRiskSeal,
  FnRouteLine,
  FnSkeleton,
  FnTable,
  useToast,
} from "../src";

describe("FnButton", () => {
  it("is a real button, type=button by default, and submit on request", () => {
    expect(mount(FnButton).attributes("type")).toBe("button");
    expect(mount(FnButton, { props: { type: "submit" } }).attributes("type")).toBe("submit");
  });

  it("disables itself and reports busy while loading", () => {
    const w = mount(FnButton, { props: { loading: true } });
    expect(w.attributes("disabled")).toBeDefined();
    expect(w.attributes("aria-busy")).toBe("true");
  });

  it("renders as a link without a button type", () => {
    const w = mount(FnButton, { props: { as: "a" }, attrs: { href: "/x" } });
    expect(w.element.tagName).toBe("A");
    expect(w.attributes("type")).toBeUndefined();
  });

  it("keeps a 44px touch target at the default size", () => {
    expect(mount(FnButton).classes()).toContain("min-h-12");
  });
});

describe("FnField + FnInput", () => {
  it("links label, hint and error to the control", () => {
    const w = mount(FnField, {
      props: { label: "Email", hint: "Work address", error: "Enter a valid email" },
      slots: {
        default: `<template #default="{ id, describedby, invalid }"><input :id="id" :aria-describedby="describedby" :aria-invalid="invalid" /></template>`,
      },
    });
    const input = w.find("input");
    const label = w.find("label");
    expect(label.attributes("for")).toBe(input.attributes("id"));
    const described = input.attributes("aria-describedby")!.split(" ");
    expect(described).toHaveLength(2);
    expect(w.find('[role="alert"]').text()).toContain("Enter a valid email");
    expect(input.attributes("aria-invalid")).toBe("true");
  });

  it("two-way binds text", async () => {
    const value = ref("a");
    const w = mount({
      components: { FnInput },
      setup: () => ({ value }),
      template: `<FnInput v-model="value" />`,
    });
    await w.find("input").setValue("hello");
    expect(value.value).toBe("hello");
  });

  it("marks invalid inputs with the danger border and aria-invalid", () => {
    const w = mount(FnInput, { props: { invalid: true } });
    expect(w.attributes("aria-invalid")).toBe("true");
    expect(w.classes()).toContain("border-oxblood-600");
  });
});

describe("FnChip", () => {
  it("emits remove from an accessible button", async () => {
    const w = mount(FnChip, {
      props: { removable: true, removeLabel: "Remove Manila" },
      slots: { default: "Manila" },
    });
    const btn = w.find("button");
    expect(btn.attributes("aria-label")).toBe("Remove Manila");
    await btn.trigger("click");
    expect(w.emitted("remove")).toHaveLength(1);
  });
});

describe("FnCheckbox", () => {
  it("renders its label inside a labelled control", () => {
    const w = mount(FnCheckbox, { props: { label: "Remember me" } });
    expect(w.find("label").text()).toContain("Remember me");
    expect(w.find('[role="checkbox"]').exists()).toBe(true);
  });
});

describe("FnRiskSeal", () => {
  it("always pairs a glyph with a word", () => {
    for (const [level, glyph] of [
      ["clear", "✓"],
      ["caution", "!"],
      ["danger", "✕"],
    ] as const) {
      const w = mount(FnRiskSeal, { props: { level, label: level.toUpperCase() } });
      expect(w.text()).toContain(glyph);
      expect(w.text()).toContain(level.toUpperCase());
      expect(w.find('[aria-hidden="true"]').exists()).toBe(true);
    }
  });
});

describe("FnPencilText", () => {
  it("shows a draft marker in pencil, and plain ink once accepted", () => {
    const draft = mount(FnPencilText, { slots: { default: "Led a team" } });
    expect(draft.classes()).toContain("text-pencil");
    expect(draft.text()).toContain("Draft");
    const ink = mount(FnPencilText, { props: { state: "ink" }, slots: { default: "Led a team" } });
    expect(ink.classes()).toContain("text-ink-900");
    expect(ink.text()).not.toContain("Draft");
  });
});

describe("FnRouteLine", () => {
  it("marks the active waypoint and exposes state to assistive tech", () => {
    const w = mount(FnRouteLine, {
      props: { steps: ["Found", "Tailored", "Applied"], active: 1, label: "Progress" },
    });
    const items = w.findAll("li");
    expect(items[1]!.attributes("aria-current")).toBe("step");
    expect(items[0]!.text()).toContain("done");
    expect(items[2]!.text()).toContain("todo");
    expect(w.find("ol").attributes("aria-label")).toBe("Progress");
  });
});

describe("FnGradeRing", () => {
  it("shows the transition and the simulation label", () => {
    const w = mount(FnGradeRing, {
      props: { grade: "A-", from: "C", simulationLabel: "Simulation" },
    });
    expect(w.text()).toContain("C");
    expect(w.text()).toContain("A-");
    expect(w.text()).toContain("Simulation");
  });
});

describe("FnTable", () => {
  const columns = [
    { key: "name", label: "Name" },
    { key: "n", label: "Count", align: "right" as const },
  ];

  it("is a semantic table with a caption and column headers", () => {
    const w = mount(FnTable, {
      props: { columns, rows: [{ id: "1", name: "A", n: 3 }], rowKey: "id", caption: "Things" },
    });
    expect(w.find("caption").text()).toBe("Things");
    expect(w.findAll('th[scope="col"]')).toHaveLength(2);
    expect(w.text()).toContain("A");
  });

  it("shows the empty message", () => {
    const w = mount(FnTable, {
      props: { columns, rows: [], rowKey: "id", caption: "Things", empty: "Nothing yet" },
    });
    expect(w.text()).toContain("Nothing yet");
  });

  it("supports cell slots and compact density", () => {
    const w = mount(FnTable, {
      props: {
        columns,
        rows: [{ id: "1", name: "A", n: 3 }],
        rowKey: "id",
        caption: "t",
        density: "compact",
      },
      slots: { "cell-name": `<template #cell-name="{ row }"><b>{{ row.name }}!</b></template>` },
    });
    expect(w.find("b").text()).toBe("A!");
    expect(w.find("td").classes()).toContain("h-10");
  });
});

describe("FnSkeleton", () => {
  it("is hidden from assistive tech and honors reduced motion", () => {
    const w = mount(FnSkeleton, { props: { lines: 3 } });
    expect(w.attributes("aria-hidden")).toBe("true");
    expect(w.element.children).toHaveLength(3);
    expect(w.element.children[0]!.className).toContain("motion-reduce:animate-none");
  });
});

describe("FnDialog", () => {
  it("renders title, description and a labelled close button when open", async () => {
    const w = mount(FnDialog, {
      props: {
        open: true,
        title: "Invite",
        description: "Send a link",
        closeLabel: "Close dialog",
      },
      slots: { default: "<p>body</p>" },
      attachTo: document.body,
    });
    await nextTick();
    const text = document.body.textContent ?? "";
    expect(text).toContain("Invite");
    expect(text).toContain("Send a link");
    expect(document.body.querySelector('[aria-label="Close dialog"]')).not.toBeNull();
    expect(document.body.querySelector('[role="dialog"]')).not.toBeNull();
    w.unmount();
  });
});

describe("useToast", () => {
  it("queues and dismisses toasts", () => {
    const { toasts, push, dismiss } = useToast();
    const id = push({ title: "Saved", tone: "success" });
    expect(toasts.value.some((t) => t.id === id && t.tone === "success")).toBe(true);
    dismiss(id);
    expect(toasts.value.some((t) => t.id === id)).toBe(false);
  });
});
