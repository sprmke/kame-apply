export type FillInstruction = {
  field_id: string;
  action: "fill" | "select" | "skip" | "checkpoint";
  value?: string | null;
  badge?: string | null;
  checkpoint_kind?: string | null;
  note?: string | null;
};

function findField(fieldId: string): HTMLElement | null {
  const idx = fieldId.lastIndexOf("#");
  const base = idx >= 0 ? fieldId.slice(0, idx) : fieldId;
  const ordinal = idx >= 0 ? Number(fieldId.slice(idx + 1)) : -1;
  const nodes = Array.from(
    document.querySelectorAll<HTMLElement>(
      "input:not([type=hidden]):not([type=submit]):not([type=button]), textarea, select",
    ),
  );
  if (ordinal >= 0 && ordinal < nodes.length) {
    const byOrd = nodes[ordinal];
    if (byOrd) {
      const id = byOrd.getAttribute("id") || byOrd.getAttribute("name") || `field_${ordinal}`;
      if (`${id}#${ordinal}` === fieldId || ordinal >= 0) return byOrd;
    }
  }
  return (
    document.getElementById(base) || document.querySelector(`[name="${CSS.escape(base)}"]`) || null
  );
}

function setNativeValue(el: HTMLElement, value: string) {
  const proto =
    el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
  const desc = Object.getOwnPropertyDescriptor(proto, "value");
  desc?.set?.call(el, value);
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
}

function badgeNear(el: HTMLElement, text: string) {
  const existing = el.parentElement?.querySelector(".kame-fill-badge");
  if (existing) existing.remove();
  const badge = document.createElement("span");
  badge.className = "kame-fill-badge";
  badge.textContent = text;
  badge.style.cssText =
    "display:inline-block;margin-left:6px;font:11px/1.2 ui-sans-serif,system-ui;" +
    "color:oklch(0.52 0.17 38);background:oklch(0.95 0.03 55);padding:2px 6px;border-radius:2px;";
  el.insertAdjacentElement("afterend", badge);
  el.style.outline = "2px solid oklch(0.66 0.18 40)";
  el.style.outlineOffset = "1px";
}

export function applyInstructions(instructions: FillInstruction[]): {
  filled: number;
  checkpoints: number;
  skipped: number;
} {
  let filled = 0;
  let checkpoints = 0;
  let skipped = 0;
  for (const instr of instructions) {
    if (instr.action === "skip") {
      skipped += 1;
      continue;
    }
    const el = findField(instr.field_id);
    if (!el) {
      skipped += 1;
      continue;
    }
    if (instr.action === "checkpoint") {
      checkpoints += 1;
      badgeNear(el, instr.badge || "Review");
      continue;
    }
    if (!instr.value) {
      skipped += 1;
      continue;
    }
    if (el instanceof HTMLSelectElement) {
      const opt = Array.from(el.options).find(
        (o) => o.value === instr.value || o.textContent?.trim() === instr.value,
      );
      if (opt) {
        el.value = opt.value;
        el.dispatchEvent(new Event("change", { bubbles: true }));
        filled += 1;
        badgeNear(el, instr.badge || "Filled");
      } else {
        checkpoints += 1;
        badgeNear(el, "Review");
      }
      continue;
    }
    if ((el as HTMLInputElement).type === "radio" || (el as HTMLInputElement).type === "checkbox") {
      const name = el.getAttribute("name");
      if (name && (el as HTMLInputElement).type === "radio") {
        const match = document.querySelector<HTMLInputElement>(
          `input[type=radio][name="${CSS.escape(name)}"][value="${CSS.escape(instr.value)}"]`,
        );
        if (match) {
          match.checked = true;
          match.dispatchEvent(new Event("change", { bubbles: true }));
          filled += 1;
          badgeNear(match, instr.badge || "Filled");
          continue;
        }
      }
      checkpoints += 1;
      badgeNear(el, "Review");
      continue;
    }
    setNativeValue(el, instr.value);
    filled += 1;
    badgeNear(el, instr.badge || "Filled");
  }
  return { filled, checkpoints, skipped };
}

/** Never click Submit / Next / Continue on restricted platforms. */
export function clickSubmitGuard(): boolean {
  // Intentionally no-op: extension never submits.
  return false;
}
