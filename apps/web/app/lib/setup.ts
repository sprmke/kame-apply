/** Pure mapping helpers for `/start`. Kept out of the page so they can be unit tested. */

export const MAX_RESUME_TEXT = 20_000;
export const MAX_SKILLS = 30;

export type QuickAnswerKey =
  "work_authorization" | "notice_period" | "salary_expectation" | "relocation";

export type AnswerWrite = {
  key: QuickAnswerKey;
  country: string | null;
  answer: string;
  approved: boolean;
};

export type QuickAnswers = {
  workCountry: string;
  workAuth: string;
  notice: string;
  salary: string;
  /** The value the page prefilled. An untouched default is a suggestion, not a claim. */
  salaryDefault: string;
  relocation: string;
};

export function normalizeCountryCode(raw: string): string {
  return raw
    .replace(/[^a-zA-Z]/g, "")
    .toUpperCase()
    .slice(0, 2);
}

/**
 * Build the quick answers that are safe to save.
 *
 * Empty fields are skipped. Work authorization needs a country because the bank key is
 * country-scoped; without one the value is never saved. Salary is the only field with a
 * prefilled default, and an untouched default stays unapproved.
 */
export function buildAnswerWrites(input: QuickAnswers): {
  writes: AnswerWrite[];
  needsCountry: boolean;
} {
  const writes: AnswerWrite[] = [];
  let needsCountry = false;

  const country = normalizeCountryCode(input.workCountry);
  const workAuth = input.workAuth.trim();
  if (workAuth) {
    if (country) {
      writes.push({
        key: "work_authorization",
        country,
        answer: workAuth,
        approved: true,
      });
    } else {
      needsCountry = true;
    }
  }

  const notice = input.notice.trim();
  if (notice) {
    writes.push({ key: "notice_period", country: null, answer: notice, approved: true });
  }

  const salary = input.salary.trim();
  if (salary) {
    writes.push({
      key: "salary_expectation",
      country: null,
      answer: salary,
      approved: salary !== input.salaryDefault.trim(),
    });
  }

  const relocation = input.relocation.trim();
  if (relocation) {
    writes.push({ key: "relocation", country: null, answer: relocation, approved: true });
  }

  return { writes, needsCountry };
}

/** Comma, semicolon, pipe, or newline separated skills, trimmed and deduped. */
export function parseSkillsInput(raw: string): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const part of (raw || "").split(/[,;|\n]+/)) {
    const name = part.trim().replace(/\s+/g, " ");
    if (!name || name.length > 120) continue;
    const key = name.toLocaleLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(name);
    if (out.length >= MAX_SKILLS) break;
  }
  return out;
}

function skillKey(name: string): string {
  return name.trim().replace(/\s+/g, " ").toLocaleLowerCase();
}

/** Skills to create: case and whitespace variants of an existing row are skipped. */
export function missingSkills(existing: string[], wanted: string[]): string[] {
  const have = new Set(existing.map(skillKey));
  return wanted.filter((name) => !have.has(skillKey(name)));
}

/** The plan endpoint accepts 20,000 characters; a long PDF is truncated, never rejected. */
export function clampResumeText(text: string): string {
  return (text || "").slice(0, MAX_RESUME_TEXT);
}

// ---- review screen helpers -------------------------------------------------------------------

export type ReviewItem = {
  id: string;
  group: string;
  target: string;
  kind: string;
  value: unknown;
  current: unknown;
  action: string;
  source: string;
  needs_you: boolean;
  needs_country: boolean;
  blocked: string;
  default_on: boolean;
  evidence: Array<{ quote: string }>;
};

export type ReviewSearch = {
  variant: string;
  name: string;
  summary: string;
  duplicate_of: string | null;
  blocked: string;
  default_on: boolean;
};

export const GROUP_ORDER = [
  "profile",
  "answers",
  "searches",
  "writing",
  "studio",
  "account",
] as const;

export function groupItems<T extends { group: string }>(items: T[]): Record<string, T[]> {
  const out: Record<string, T[]> = {};
  for (const item of items) {
    (out[item.group] ??= []).push(item);
  }
  return out;
}

const FIELD_KEYS: Record<string, string> = {
  "profile.display_name": "setup.field.name",
  "profile.headline": "setup.field.headline",
  "profile.summary": "setup.field.summary",
  "profile.location": "setup.field.location",
  "profile.timezone": "setup.field.timezone",
  "profile.language": "setup.field.language",
  "profile.links": "setup.field.links",
  "profile.salary_prefs": "setup.field.lowestPay",
  "profile.work_authorization": "setup.field.workAuthorization",
  "profile.experience": "setup.field.experience",
  "profile.project": "setup.field.project",
  "profile.education": "setup.field.education",
  "profile.certification": "setup.field.certification",
  "profile.spoken_language": "setup.field.spokenLanguage",
  "profile.skill": "setup.field.skill",
  "writing.preset": "setup.field.writingStyle",
  "studio.base_resume": "setup.field.baseResume",
  "account.name": "setup.field.accountName",
  "account.timezone": "setup.field.accountTimezone",
  "industry.field": "setup.field.fieldOfWork",
};

export function fieldKey(target: string): string {
  if (target.startsWith("answers.")) return "setup.field.answer";
  return FIELD_KEYS[target] ?? "setup.field.other";
}

export function itemValueText(item: ReviewItem): string {
  const value = item.value;
  if (item.needs_you) return "";
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (Array.isArray(value)) {
    return value
      .map((row) => (typeof row === "string" ? row : String((row as { url?: string }).url ?? "")))
      .filter(Boolean)
      .join(", ");
  }
  if (typeof value === "object") {
    const row = value as Record<string, unknown>;
    if (item.target === "profile.experience") {
      const title = String(row.title ?? "");
      const company = String(row.company ?? "");
      return [title, company && `at ${company}`].filter(Boolean).join(" ");
    }
    if (
      [
        "profile.skill",
        "profile.spoken_language",
        "profile.certification",
        "profile.education",
        "profile.project",
      ].includes(item.target)
    ) {
      const name = String(row.name ?? row.institution ?? "");
      const years = row.years ? ` · ${row.years} yrs` : "";
      return `${name}${years}`.trim();
    }
    if (item.target === "profile.salary_prefs") {
      const amount = Number(row.floor ?? 0);
      return `${String(row.currency ?? "")} ${amount.toLocaleString()} a ${String(row.period ?? "month")}`.trim();
    }
    if (item.target === "studio.base_resume") {
      return `${String(row.label ?? "")} · ${String(row.page_size ?? "").toUpperCase()}`;
    }
    if ("answer" in row) return String(row.answer ?? "");
    return Object.values(row)
      .filter((v) => typeof v === "string" || typeof v === "number")
      .join(", ");
  }
  return String(value);
}

export function answerSlotKey(item: ReviewItem): string {
  const parts = item.target.split(".");
  return parts[2] ? `${parts[1]}.${parts[2]}` : (parts[1] ?? item.target);
}

export type LowestPay = {
  amount: number;
  currency: string;
  period: "hour" | "day" | "month" | "year";
};

export type Decisions = {
  items: Record<
    string,
    { action: string; value: unknown; edited: boolean; country?: string | null }
  >;
  searches: Record<string, unknown>;
  lowest_pay: LowestPay | null;
  lowest_pay_set: boolean;
  seen_pages: string[];
};

export function decisionFor(decisions: Decisions, item: ReviewItem) {
  return decisions.items[item.id] ?? { action: item.action, value: null, edited: false };
}

export function isKept(decisions: Decisions, item: ReviewItem): boolean {
  const action = decisionFor(decisions, item).action;
  if (item.blocked !== "ok") return false;
  return !["skip", "keep_current"].includes(action);
}

export function setKept(decisions: Decisions, item: ReviewItem, kept: boolean): Decisions {
  return {
    ...decisions,
    items: {
      ...decisions.items,
      [item.id]: {
        ...decisionFor(decisions, item),
        action: kept ? (item.action === "keep_current" ? "add" : item.action) : "skip",
      },
    },
  };
}

export function setValue(
  decisions: Decisions,
  item: ReviewItem,
  value: unknown,
  country?: string | null,
): Decisions {
  const previous = decisionFor(decisions, item) as { country?: string | null };
  const next: { action: string; value: unknown; edited: boolean; country?: string | null } = {
    action: "add",
    value,
    edited: true,
  };
  const chosen = country === undefined ? previous.country : country;
  if (chosen) next.country = chosen;
  return { ...decisions, items: { ...decisions.items, [item.id]: next } };
}

export function salaryText(pay: LowestPay): string {
  return `${pay.currency} ${pay.amount.toLocaleString()} a ${pay.period}`;
}

export function parseAmount(raw: string): number | null {
  const cleaned = (raw || "").replace(/[^0-9.]/g, "");
  if (!cleaned) return null;
  const value = Number(cleaned);
  return Number.isFinite(value) && value > 0 ? value : null;
}

export function searchTitleText(proposal: {
  criteria?: { titles?: Array<{ title: string; exclude?: boolean }> };
}): string {
  return (proposal.criteria?.titles ?? [])
    .filter((row) => !row.exclude)
    .map((row) => row.title)
    .join(", ");
}

export function searchSkillText(
  proposal: { criteria?: { skills?: { must?: string[]; nice?: string[] } } },
  key: "must" | "nice",
): string {
  return (proposal.criteria?.skills?.[key] ?? []).join(", ");
}

export function withTitles<
  T extends {
    criteria: { titles: Array<{ title: string; synonyms: string[]; exclude: boolean }> };
  },
>(proposal: T, raw: string): T {
  const titles = raw
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean)
    .slice(0, 5)
    .map((title, index) => ({
      title,
      synonyms: index === 0 ? (proposal.criteria.titles[0]?.synonyms ?? []) : [],
      exclude: false,
    }));
  return { ...proposal, criteria: { ...proposal.criteria, titles } };
}

export function withSkills<
  T extends { criteria: { skills: { must: string[]; nice: string[]; exclude: string[] } } },
>(proposal: T, key: "must" | "nice", raw: string): T {
  const values = raw
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean)
    .slice(0, key === "must" ? 6 : 10);
  return {
    ...proposal,
    criteria: { ...proposal.criteria, skills: { ...proposal.criteria.skills, [key]: values } },
  };
}

export function criteriaSummary(criteria: {
  titles?: Array<{ title: string; exclude?: boolean }>;
  skills?: { must?: string[] };
  locations?: Array<{ place?: string }>;
  work_modes?: string[];
}): string {
  const titles = (criteria.titles ?? [])
    .filter((row) => !row.exclude)
    .map((row) => row.title)
    .join(", ");
  const must = (criteria.skills?.must ?? []).join(", ");
  const place = criteria.locations?.[0]?.place ?? "";
  const modes = (criteria.work_modes ?? [])
    .map((mode) => mode.replace("on_site", "on-site"))
    .join(", ");
  return [titles, must, place, modes].filter(Boolean).join(" · ");
}

export function summarySentence(counts: Record<string, number>): string {
  const parts: string[] = [];
  if (counts.profile) parts.push(`${counts.profile} profile additions`);
  if (counts.answers) parts.push(`${counts.answers} answers`);
  if (counts.searches)
    parts.push(`${counts.searches} ${counts.searches === 1 ? "search" : "searches"}`);
  return parts.join(", ");
}

export function searchDecisionKey(variant: string): string {
  return `searches.${variant}`;
}

export function isSearchKept(decisions: Decisions, search: ReviewSearch): boolean {
  if (search.blocked !== "ok") return false;
  const decision = decisions.items[searchDecisionKey(search.variant)];
  if (decision) return !["skip", "keep_current"].includes(decision.action);
  return search.default_on;
}

export function setSearchKept(
  decisions: Decisions,
  search: ReviewSearch,
  kept: boolean,
): Decisions {
  return {
    ...decisions,
    items: {
      ...decisions.items,
      [searchDecisionKey(search.variant)]: {
        action: kept ? "add" : "skip",
        value: null,
        edited: false,
      },
    },
  };
}

const ANSWER_LABEL_KEYS: Record<string, string> = {
  work_authorization: "setup.answer.workAuth",
  sponsorship: "setup.answer.sponsorship",
  notice_period: "setup.answer.notice",
  salary_expectation: "setup.answer.salary",
  relocation: "setup.answer.relocation",
  remote_preference: "setup.answer.remote",
  linkedin_url: "setup.answer.linkedin",
  github_url: "setup.answer.github",
  portfolio_url: "setup.answer.portfolio",
  how_did_you_hear: "setup.answer.howDidYouHear",
  eeo_race: "setup.answer.eeoRace",
  eeo_gender: "setup.answer.eeoGender",
  eeo_veteran: "setup.answer.eeoVeteran",
  eeo_disability: "setup.answer.eeoDisability",
};

export function answerLabelKey(target: string): string {
  const key = target.split(".")[1] ?? "";
  return ANSWER_LABEL_KEYS[key] ?? "setup.answer.other";
}

/** Country-scoped answers say which country, for example "Work authorization (PH)". */
export function answerCountry(target: string): string {
  return target.split(".")[2] ?? "";
}
