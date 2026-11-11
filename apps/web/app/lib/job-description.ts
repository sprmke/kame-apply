export type JobDescriptionSectionKind = "prose" | "list" | "tools";

export type JobDescriptionSection = {
  title: string;
  kind: JobDescriptionSectionKind;
  paragraphs: string[];
  bullets: string[];
  tools: string[];
};

const HEADINGS = [
  "The Role",
  "What Work Looks Like",
  "Every day",
  "Delighting customers",
  "Making support smarter with AI",
  "Keeping the product solid",
  "Running the week",
  "Tools you'll use:",
  "Who You Are",
  "A Plus If You Have",
  "How We Work Together",
  "Benefits",
  "About the role",
  "About us",
  "About the team",
  "The team",
  "Responsibilities",
  "What you'll do",
  "What you will do",
  "Requirements",
  "Qualifications",
  "What we're looking for",
  "Nice to have",
  "Preferred qualifications",
  "Perks",
  "Compensation",
  "How to apply",
  "Our stack",
  "Why join us",
];

const LIST_HEADINGS = new Set([
  "Every day",
  "Delighting customers",
  "Making support smarter with AI",
  "Keeping the product solid",
  "Running the week",
  "Who You Are",
  "A Plus If You Have",
  "Benefits",
  "Responsibilities",
  "What you'll do",
  "What you will do",
  "Requirements",
  "Qualifications",
  "What we're looking for",
  "Nice to have",
  "Preferred qualifications",
  "Perks",
]);

const TOOL_HEADINGS = new Set(["Tools you'll use"]);

const HEADING_RE = new RegExp(`(${HEADINGS.map(escapeRegExp).join("|")})`, "g");

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function normalizeText(raw: string): string {
  return raw
    .replace(/\r\n?/g, "\n")
    .replace(/â\u0084¢/g, "™")
    .replace(/â\u0080\u0099/g, "’")
    .replace(/â\u0080\u009c/g, "“")
    .replace(/â\u0080\u009d/g, "”")
    .replace(/â\u0080\u0093/g, "–")
    .replace(/â\u0080\u0094/g, "—")
    .replace(/â\u0080\u00a6/g, "…")
    .replace(/â\u0080\u00a2/g, "•")
    .replace(/â„¢/g, "™")
    .replace(/â€™/g, "’")
    .replace(/â€˜/g, "‘")
    .replace(/â€œ/g, "“")
    .replace(/â€”/g, "—")
    .replace(/â€“/g, "–")
    .replace(/â€¦/g, "…")
    .replace(/â€¢/g, "•")
    .replace(/\u00c2\u00a0/g, " ")
    .replace(/\u00a0/g, " ")
    .replace(/[\u200B-\u200D\uFEFF]/g, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/__(.+?)__/g, "$1")
    .replace(/[ \t]+/g, " ")
    .replace(/ *\n */g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

function splitSentences(text: string): string[] {
  return text
    .replace(/\s+/g, " ")
    .trim()
    .split(/(?<=[.!?])\s+(?=[A-Z0-9"'“”‘’(])/g)
    .map((sentence) => sentence.trim())
    .filter(Boolean);
}

function groupSentences(sentences: string[], size = 3): string[] {
  const paragraphs: string[] = [];
  for (let i = 0; i < sentences.length; i += size) {
    paragraphs.push(sentences.slice(i, i + size).join(" "));
  }
  return paragraphs;
}

function explicitParagraphs(text: string): string[] {
  return text
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.replace(/\s+/g, " ").trim())
    .filter(Boolean);
}

function cleanListItem(item: string): string {
  return item
    .replace(/^\s*(?:[-*•–]|\d+[.)])\s*/, "")
    .replace(/\s+/g, " ")
    .trim();
}

function toolsFromText(text: string): string[] {
  return [
    ...new Set(
      text
        .replace(/\s+/g, " ")
        .replace(/\band\b/gi, ",")
        .split(",")
        .map((tool) =>
          cleanListItem(tool)
            .replace(/[.!]+$/, "")
            .trim(),
        )
        .filter((tool) => tool.length > 0),
    ),
  ];
}

function makeSection(title: string, body: string): JobDescriptionSection {
  const kind: JobDescriptionSectionKind = TOOL_HEADINGS.has(title)
    ? "tools"
    : LIST_HEADINGS.has(title)
      ? "list"
      : "prose";

  if (kind === "tools") {
    return { title, kind, paragraphs: [], bullets: [], tools: toolsFromText(body) };
  }

  if (kind === "list") {
    const lines = body.split("\n").map(cleanListItem).filter(Boolean);
    const bullets = lines.length > 1 ? lines : splitSentences(body).map(cleanListItem);
    return { title, kind, paragraphs: [], bullets, tools: [] };
  }

  const paragraphs = explicitParagraphs(body).flatMap((paragraph) => {
    const sentences = splitSentences(paragraph);
    return sentences.length > 1 ? groupSentences(sentences) : [paragraph];
  });

  return { title, kind, paragraphs, bullets: [], tools: [] };
}

/** Format a plain-text job posting into readable sections without changing its facts. */
export function formatJobDescription(raw: string | null | undefined): JobDescriptionSection[] {
  const text = normalizeText(raw ?? "");
  if (!text) return [];

  const parts = text.split(HEADING_RE);
  const intro = parts.shift()?.trim() ?? "";
  const sections: JobDescriptionSection[] = [];

  if (intro) sections.push(makeSection("Overview", intro));

  for (let i = 0; i < parts.length; i += 2) {
    const title = parts[i]?.replace(/:$/, "").trim();
    const body = parts[i + 1]?.trim() ?? "";
    if (!title || !body) continue;
    sections.push(makeSection(title, body));
  }

  if (!sections.length) return [makeSection("Overview", text)];
  return sections;
}
