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
      const instructions = ((msg as { instructions?: FillInstruction[] }).instructions ||
        []) as FillInstruction[];
      return Promise.resolve(applyInstructions(instructions));
    }
    if (type === "kame.focused") {
      const el = document.activeElement as HTMLElement | null;
      if (!el) return Promise.resolve({ question: "" });
      const label =
        el.getAttribute("aria-label") ||
        (el as HTMLInputElement).placeholder ||
        el.closest("label")?.textContent ||
        "";
      return Promise.resolve({ question: String(label).trim().slice(0, 500) });
    }
    return undefined;
  });
});
