import { describe, expect, it } from "vitest";
import { formatJobDescription } from "../app/lib/job-description";

const posting =
  "QuickMail is a cold email platform for teams. We have run since 2014. " +
  "The Role We are hiring a support person. You own the customer relationship. You work with engineering. " +
  "What Work Looks Like Every day Set priorities. Triage tickets. Check the dashboard. " +
  "Tools you'll use: Helpscout, GitHub, Postmark and Slack. " +
  "Who You Are You build rapport fast. You are warm and clear. " +
  "Benefits Contract type: full-time. Compensation: $2,500 to $4,000 per month.";

describe("formatJobDescription", () => {
  it("splits known posting headings into readable sections", () => {
    const sections = formatJobDescription(posting);
    expect(sections.map((section) => section.title)).toEqual([
      "Overview",
      "The Role",
      "Every day",
      "Tools you'll use",
      "Who You Are",
      "Benefits",
      "Compensation",
    ]);
    expect(
      sections.find((section) => section.title === "The Role")?.paragraphs.length,
    ).toBeGreaterThan(0);
    expect(sections.find((section) => section.title === "Every day")?.kind).toBe("list");
    expect(sections.find((section) => section.title === "Benefits")?.bullets).toHaveLength(1);
    expect(sections.find((section) => section.title === "Compensation")?.paragraphs).toHaveLength(
      1,
    );
  });

  it("formats tools as separate items", () => {
    const tools = formatJobDescription(posting).find(
      (section) => section.title === "Tools you'll use",
    );
    expect(tools?.tools).toEqual(["Helpscout", "GitHub", "Postmark", "Slack"]);
  });

  it("repairs common mojibake and removes markdown emphasis", () => {
    const sections = formatJobDescription(
      "We build Inbox rotationâ\u0084¢ tools. Please mention **TRUMP** when applying.",
    );
    expect(sections[0]?.paragraphs.join(" ")).toContain("Inbox rotation™ tools");
    expect(sections[0]?.paragraphs.join(" ")).toContain("Please mention TRUMP");
    expect(sections[0]?.paragraphs.join(" ")).not.toContain("**");
  });

  it("falls back to one overview when there are no known headings", () => {
    const sections = formatJobDescription(
      "A short posting without headings. It has two sentences.",
    );
    expect(sections).toHaveLength(1);
    expect(sections[0]?.title).toBe("Overview");
    expect(sections[0]?.paragraphs[0]).toContain("A short posting");
  });

  it("returns nothing for empty text", () => {
    expect(formatJobDescription("")).toEqual([]);
    expect(formatJobDescription(null)).toEqual([]);
  });
});
