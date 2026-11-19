import { describe, expect, it } from "vitest";
import {
  answerCountry,
  criteriaSummary,
  answerLabelKey,
  answerSlotKey,
  buildAnswerWrites,
  decisionFor,
  fieldKey,
  groupItems,
  isKept,
  isSearchKept,
  parseAmount,
  salaryText,
  searchSkillText,
  searchTitleText,
  withSkills,
  withTitles,
  itemValueText,
  setKept,
  setSearchKept,
  setValue,
  summarySentence,
  clampResumeText,
  MAX_RESUME_TEXT,
  missingSkills,
  normalizeCountryCode,
  parseSkillsInput,
} from "../app/lib/setup";

const empty = {
  workCountry: "",
  workAuth: "",
  notice: "",
  salary: "",
  salaryDefault: "Open to discussion",
  relocation: "",
};

describe("quick answers", () => {
  it("saves nothing when every field is empty", () => {
    expect(buildAnswerWrites(empty)).toEqual({ writes: [], needsCountry: false });
  });

  it("saves work authorization only with a country", () => {
    const withCountry = buildAnswerWrites({ ...empty, workCountry: "ph", workAuth: "Citizen" });
    expect(withCountry.needsCountry).toBe(false);
    expect(withCountry.writes).toEqual([
      { key: "work_authorization", country: "PH", answer: "Citizen", approved: true },
    ]);

    const withoutCountry = buildAnswerWrites({ ...empty, workAuth: "Citizen" });
    expect(withoutCountry.needsCountry).toBe(true);
    expect(withoutCountry.writes).toEqual([]);
  });

  it("keeps an untouched salary default unapproved", () => {
    const { writes } = buildAnswerWrites({ ...empty, salary: "Open to discussion" });
    expect(writes).toEqual([
      {
        key: "salary_expectation",
        country: null,
        answer: "Open to discussion",
        approved: false,
      },
    ]);
  });

  it("approves a salary the user typed", () => {
    const { writes } = buildAnswerWrites({ ...empty, salary: "PHP 60,000 a month" });
    expect(writes[0].approved).toBe(true);
  });

  it("saves each stated answer independently", () => {
    const { writes } = buildAnswerWrites({
      workCountry: "PH",
      workAuth: "Authorized",
      notice: "30 days",
      salary: "PHP 60,000",
      salaryDefault: "Open to discussion",
      relocation: "Within Metro Manila",
    });
    expect(writes.map((w) => w.key)).toEqual([
      "work_authorization",
      "notice_period",
      "salary_expectation",
      "relocation",
    ]);
  });
});

describe("country codes", () => {
  it("keeps two letters and uppercases them", () => {
    expect(normalizeCountryCode(" ph ")).toBe("PH");
    expect(normalizeCountryCode("usa")).toBe("US");
    expect(normalizeCountryCode("")).toBe("");
    expect(normalizeCountryCode("1p")).toBe("P");
  });
});

describe("skills", () => {
  it("splits on commas, semicolons, pipes, and newlines", () => {
    expect(parseSkillsInput("React, TypeScript; CSS|HTML\nSQL")).toEqual([
      "React",
      "TypeScript",
      "CSS",
      "HTML",
      "SQL",
    ]);
  });

  it("trims, collapses spaces, and dedupes case-insensitively", () => {
    expect(parseSkillsInput("  React  , react,  Node   JS ")).toEqual(["React", "Node JS"]);
  });

  it("drops empty parts and caps the list", () => {
    expect(parseSkillsInput(",, ; | ")).toEqual([]);
    const many = Array.from({ length: 40 }, (_, i) => `Skill ${i}`).join(", ");
    expect(parseSkillsInput(many)).toHaveLength(30);
  });

  it("skips skills that already exist, ignoring case and spacing", () => {
    expect(missingSkills(["React", "Node  JS"], ["react", "Node JS", "CSS"])).toEqual(["CSS"]);
  });
});

describe("resume text", () => {
  it("clamps long text instead of rejecting it", () => {
    const long = "a".repeat(MAX_RESUME_TEXT + 500);
    expect(clampResumeText(long)).toHaveLength(MAX_RESUME_TEXT);
    expect(clampResumeText("short")).toBe("short");
  });
});

const item = {
  id: "profile.headline",
  group: "profile",
  target: "profile.headline",
  kind: "value",
  value: "Frontend engineer",
  current: null,
  action: "add",
  source: "resume",
  needs_you: false,
  blocked: "ok",
  default_on: true,
  evidence: [],
};

describe("review helpers", () => {
  it("groups items in page order", () => {
    const groups = groupItems([
      { ...item, group: "answers" },
      { ...item, group: "profile" },
    ]);
    expect(Object.keys(groups)).toEqual(["answers", "profile"]);
  });

  it("maps targets to field keys", () => {
    expect(fieldKey("profile.headline")).toBe("setup.field.headline");
    expect(fieldKey("answers.notice_period")).toBe("setup.field.answer");
    expect(fieldKey("profile.unknown")).toBe("setup.field.other");
    expect(fieldKey("profile.skill")).toBe("setup.field.skill");
  });

  it("formats every value shape", () => {
    expect(itemValueText(item as never)).toBe("Frontend engineer");
    expect(
      itemValueText({
        ...item,
        target: "profile.experience",
        value: { title: "Engineer", company: "Acme" },
      } as never),
    ).toBe("Engineer at Acme");
    expect(
      itemValueText({
        ...item,
        target: "profile.skill",
        value: { name: "React", years: 3 },
      } as never),
    ).toBe("React · 3 yrs");
    expect(
      itemValueText({
        ...item,
        target: "studio.base_resume",
        value: { label: "Base", page_size: "a4" },
      } as never),
    ).toBe("Base · A4");
    expect(
      itemValueText({
        ...item,
        target: "answers.notice_period",
        value: { answer: "30 days" },
      } as never),
    ).toBe("30 days");
    expect(itemValueText({ ...item, needs_you: true, value: null } as never)).toBe("");
  });

  it("keeps rows by default and toggles skip", () => {
    const decisions = { items: {}, seen_pages: [] };
    expect(isKept(decisions, item as never)).toBe(true);
    const skipped = setKept(decisions, item as never, false);
    expect(isKept(skipped, item as never)).toBe(false);
    expect(decisionFor(skipped, item as never).action).toBe("skip");
  });

  it("never keeps a blocked row", () => {
    const decisions = { items: {}, seen_pages: [] };
    expect(isKept(decisions, { ...item, blocked: "duplicate" } as never)).toBe(false);
  });

  it("records an edited value", () => {
    const decisions = setValue({ items: {}, seen_pages: [] }, item as never, "Designer");
    expect(decisions.items["profile.headline"]).toEqual({
      action: "add",
      value: "Designer",
      edited: true,
    });
  });

  it("carries the country on a country-scoped answer", () => {
    const auth = {
      ...item,
      id: "answers.work_authorization",
      group: "answers",
      target: "answers.work_authorization",
      value: null,
      needs_you: true,
      needs_country: true,
    };
    const decisions = setValue(
      { items: {}, seen_pages: [] },
      auth as never,
      { answer: "Yes", approved: true },
      "PH",
    );
    expect(decisions.items["answers.work_authorization"]).toEqual({
      action: "add",
      value: { answer: "Yes", approved: true },
      edited: true,
      country: "PH",
    });
    expect(setKept(decisions, auth as never, false).items["answers.work_authorization"]).toEqual({
      action: "skip",
      value: { answer: "Yes", approved: true },
      edited: true,
      country: "PH",
    });
  });

  it("labels answer rows", () => {
    expect(answerLabelKey("answers.notice_period")).toBe("setup.answer.notice");
    expect(answerLabelKey("answers.work_authorization.PH")).toBe("setup.answer.workAuth");
    expect(answerLabelKey("answers.custom_thing")).toBe("setup.answer.other");
    expect(answerLabelKey("answers.eeo_race")).toBe("setup.answer.eeoRace");
    expect(answerCountry("answers.work_authorization.PH")).toBe("PH");
    expect(answerCountry("answers.notice_period")).toBe("");
  });

  it("keeps answers keyed by key and country", () => {
    expect(answerSlotKey({ ...item, target: "answers.work_authorization.PH" } as never)).toBe(
      "work_authorization.PH",
    );
    expect(answerSlotKey({ ...item, target: "answers.notice_period" } as never)).toBe(
      "notice_period",
    );
  });

  it("toggles searches by variant", () => {
    const decisions = { items: {}, seen_pages: [] };
    const search = {
      variant: "same_role",
      name: "Frontend engineer",
      summary: "",
      duplicate_of: null,
      blocked: "ok",
      default_on: true,
    };
    expect(isSearchKept(decisions, search)).toBe(true);
    expect(isSearchKept(setSearchKept(decisions, search, false), search)).toBe(false);
  });

  it("builds a summary sentence from counts", () => {
    expect(summarySentence({ profile: 6, answers: 9, searches: 1 })).toBe(
      "6 profile additions, 9 answers, 1 search",
    );
    expect(summarySentence({})).toBe("");
  });
});

describe("salary and search editing", () => {
  it("parses an amount and formats it", () => {
    expect(parseAmount("45,000")).toBe(45000);
    expect(parseAmount("")).toBeNull();
    expect(parseAmount("abc")).toBeNull();
    expect(salaryText({ amount: 45000, currency: "PHP", period: "month" })).toBe(
      "PHP 45,000 a month",
    );
  });

  it("reads titles and skills for the edit sheet", () => {
    const search = {
      criteria: {
        titles: [
          { title: "Support Lead", synonyms: ["Support Manager"], exclude: false },
          { title: "Old title", synonyms: [], exclude: true },
        ],
        skills: { must: ["Zendesk"], nice: ["Salesforce"], exclude: [] },
      },
    };
    expect(searchTitleText(search as never)).toBe("Support Lead");
    expect(searchSkillText(search as never, "must")).toBe("Zendesk");
  });

  it("rebuilds titles and skills without losing the synonym", () => {
    const search = {
      criteria: {
        titles: [{ title: "Support Lead", synonyms: ["Support Manager"], exclude: false }],
        skills: { must: ["Zendesk"], nice: [], exclude: [] },
      },
    };
    const titled = withTitles(search as never, "Support Operations Lead, Support Manager");
    expect(titled.criteria.titles.map((row) => row.title)).toEqual([
      "Support Operations Lead",
      "Support Manager",
    ]);
    expect(titled.criteria.titles[0]?.synonyms).toEqual(["Support Manager"]);
    const skilled = withSkills(search as never, "must", "Zendesk, QA");
    expect(skilled.criteria.skills.must).toEqual(["Zendesk", "QA"]);
  });

  it("summarizes edited criteria", () => {
    expect(
      criteriaSummary({
        titles: [{ title: "Support Lead", exclude: false }],
        skills: { must: ["Zendesk"] },
        locations: [{ place: "Manila" }],
        work_modes: ["remote", "on_site"],
      }),
    ).toBe("Support Lead · Zendesk · Manila · remote, on-site");
  });
});
