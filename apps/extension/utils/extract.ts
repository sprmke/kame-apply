// Never read or transmit these values, whatever the input type or autocomplete token says.
const SENSITIVE_LABEL =
  /(ssn|social\s*security|national\s*id|passport|tax\s*id|bank|account\s*number|routing|iban|swift|card\s*number|credit\s*card|date\s*of\s*birth|birth\s*date|dob)/i;
const SENSITIVE_AUTOCOMPLETE = /^(cc-|current-password|new-password|one-time-code|bday|sex$|tax$)/i;

export function isSensitiveField(el: HTMLElement, label: string): boolean {
  const input = el as HTMLInputElement;
  if ((input.type || "").toLowerCase() === "password") return true;
  const ac = (el.getAttribute("autocomplete") || "").trim();
  if (ac && SENSITIVE_AUTOCOMPLETE.test(ac)) return true;
  const name = el.getAttribute("name") || "";
  return SENSITIVE_LABEL.test(`${label} ${name}`);
}

export type ExtractedField = {
  id: string;
  label: string;
  name: string;
  type: string;
  autocomplete: string;
  required: boolean;
  options: string[];
  value: string;
  section: string;
  maxlength: number | null;
  surrounding_text: string;
};

function labelFor(el: HTMLElement): string {
  const id = el.getAttribute("id");
  if (id) {
    const lab = document.querySelector(`label[for="${CSS.escape(id)}"]`);
    if (lab?.textContent) return lab.textContent.trim();
  }
  const aria = el.getAttribute("aria-label");
  if (aria) return aria.trim();
  const wrapped = el.closest("label");
  if (wrapped?.textContent) return wrapped.textContent.trim().slice(0, 200);
  const prev = el.previousElementSibling;
  if (prev && /label|span|p|div/i.test(prev.tagName) && prev.textContent) {
    return prev.textContent.trim().slice(0, 200);
  }
  return (el.getAttribute("placeholder") || "").trim();
}

function fieldType(el: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement): string {
  if (el instanceof HTMLSelectElement) return "select";
  if (el instanceof HTMLTextAreaElement) return "textarea";
  return (el.type || "text").toLowerCase();
}

function optionsOf(el: HTMLElement): string[] {
  if (el instanceof HTMLSelectElement) {
    return Array.from(el.options)
      .map((o) => o.textContent?.trim() || o.value)
      .filter(Boolean);
  }
  const name = el.getAttribute("name");
  if (name && (el as HTMLInputElement).type === "radio") {
    return Array.from(
      document.querySelectorAll<HTMLInputElement>(
        `input[type="radio"][name="${CSS.escape(name)}"]`,
      ),
    ).map((r) => r.value || labelFor(r));
  }
  return [];
}

export function extractFields(root: ParentNode = document): ExtractedField[] {
  const nodes = root.querySelectorAll<HTMLElement>(
    "input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=image]), textarea, select",
  );
  const out: ExtractedField[] = [];
  let i = 0;
  for (const el of Array.from(nodes)) {
    if ((el as HTMLInputElement).disabled) continue;
    const type = fieldType(el as HTMLInputElement);
    // Never read sensitive values from the page for transmission.
    const label = labelFor(el);
    const sensitiveType = isSensitiveField(el, label);
    const id = el.getAttribute("id") || el.getAttribute("name") || `field_${i}`;
    const section =
      el
        .closest("fieldset, section, [role=group]")
        ?.querySelector("legend, h2, h3")
        ?.textContent?.trim() || "";
    out.push({
      id: `${id}#${i}`,
      label,
      name: el.getAttribute("name") || "",
      type,
      autocomplete: el.getAttribute("autocomplete") || "",
      required: el.hasAttribute("required") || el.getAttribute("aria-required") === "true",
      options: optionsOf(el),
      value: sensitiveType ? "" : ((el as HTMLInputElement).value || "").slice(0, 200),
      section,
      maxlength: (el as HTMLInputElement).maxLength > 0 ? (el as HTMLInputElement).maxLength : null,
      surrounding_text: (el.parentElement?.textContent || "").trim().slice(0, 240),
    });
    i += 1;
  }
  return out;
}

export function extractJobHints(): {
  title: string;
  company: string;
  description_text: string;
  json_ld: Record<string, unknown> | null;
} {
  let jsonLd: Record<string, unknown> | null = null;
  for (const script of Array.from(
    document.querySelectorAll('script[type="application/ld+json"]'),
  )) {
    try {
      const data = JSON.parse(script.textContent || "");
      const items = Array.isArray(data) ? data : [data];
      for (const item of items) {
        if (item && (item["@type"] === "JobPosting" || item["@type"]?.includes?.("Job"))) {
          jsonLd = item;
          break;
        }
      }
    } catch {
      /* ignore */
    }
    if (jsonLd) break;
  }
  const title =
    (jsonLd?.title as string) ||
    document.querySelector("h1")?.textContent?.trim() ||
    document.title;
  const company =
    (typeof jsonLd?.hiringOrganization === "object" &&
      jsonLd?.hiringOrganization &&
      ((jsonLd.hiringOrganization as { name?: string }).name || "")) ||
    "";
  const description_text = (
    (jsonLd?.description as string) ||
    document.querySelector("[data-testid='job-description'], .job-description, #job-description")
      ?.textContent ||
    ""
  )
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 8000);
  return { title, company, description_text, json_ld: jsonLd };
}
