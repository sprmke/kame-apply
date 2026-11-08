/**
 * Injected into the active tab on user gesture (not a declared content_script).
 * Keeps required host_permissions empty; optional hosts are requested at use time.
 */
import { extractFields, extractJobHints } from "../utils/extract";
import { applyInstructions, type FillInstruction } from "../utils/fill";
import { detectPlatform, isConfirmationUrl } from "../utils/platforms";

export default defineUnlistedScript(() => {
  const w = globalThis as typeof globalThis & {
    __kamePageBridge?: boolean;
  };
  if (w.__kamePageBridge) return;
  w.__kamePageBridge = true;

  // Clicking the side panel can move focus out of the page; remember the last form field.
  let lastFocused: HTMLElement | null = null;
  const isField = (el: EventTarget | null): el is HTMLElement =>
    el instanceof HTMLElement && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName);
  document.addEventListener(
    "focusin",
    (e) => {
      if (isField(e.target)) lastFocused = e.target;
    },
    true,
  );
  const focusedField = (): HTMLElement | null =>
    isField(document.activeElement) ? document.activeElement : lastFocused;
  const fieldId = (el: HTMLElement | null): string =>
    el ? el.id || el.getAttribute("name") || "" : "";

  browser.runtime.onMessage.addListener((msg) => {
    if (!msg || typeof msg !== "object") return;
    const type = (msg as { type?: string }).type;
    if (type === "kame.extract") {
      return Promise.resolve({
        fields: extractFields(),
        hints: extractJobHints(),
        url: location.href,
        platform: detectPlatform(location.href),
        confirmation: isConfirmationUrl(location.href, detectPlatform(location.href)),
        pageText: document.body?.innerText?.slice(0, 4000) || "",
      });
    }
    if (type === "kame.fill") {
      const raw = ((msg as { instructions?: FillInstruction[] }).instructions ||
        []) as FillInstruction[];
      const target = fieldId(focusedField());
      const instructions = raw.map((instr) =>
        instr.field_id === "focused" && target ? { ...instr, field_id: target } : instr,
      );
      return Promise.resolve(applyInstructions(instructions));
    }
    if (type === "kame.focused") {
      const el = focusedField();
      if (!el) return Promise.resolve({ question: "", field_id: "" });
      const label =
        el.getAttribute("aria-label") ||
        (el as HTMLInputElement).placeholder ||
        el.closest("label")?.textContent ||
        "";
      return Promise.resolve({
        question: String(label).trim().slice(0, 500),
        field_id: fieldId(el),
      });
    }
    return undefined;
  });
});
