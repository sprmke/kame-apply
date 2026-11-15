import { describe, expect, it } from "vitest";
import { buildMatchGrammar, segmentText, type MatchTerm } from "../app/lib/job-highlights";

const term = (overrides: Partial<MatchTerm>): MatchTerm => ({
  key: "x",
  label: "X",
  patterns: ["X"],
  verdict: "met",
  ...overrides,
});

function marked(text: string, terms: MatchTerm[]): string[] {
  return segmentText(text, buildMatchGrammar(terms))
    .filter((segment) => segment.term)
    .map((segment) => segment.text);
}

describe("job highlights", () => {
  it("returns plain text when there are no terms", () => {
    expect(segmentText("Hello", buildMatchGrammar([]))).toEqual([{ text: "Hello" }]);
  });

  it("marks matched terms and keeps the surrounding text", () => {
    const segments = segmentText(
      "We use React and Python.",
      buildMatchGrammar([
        term({ key: "react", label: "React", patterns: ["React"] }),
        term({ key: "python", label: "Python", patterns: ["Python"], verdict: "gap" }),
      ]),
    );
    expect(segments.map((s) => s.text)).toEqual(["We use ", "React", " and ", "Python", "."]);
    expect(segments[1]?.term?.verdict).toBe("met");
    expect(segments[3]?.term?.verdict).toBe("gap");
  });

  it("prefers the longest surface form", () => {
    expect(
      marked("React.js and React Native", [
        term({ key: "react", label: "React", patterns: ["React", "React.js"] }),
        term({ key: "rn", label: "React Native", patterns: ["React Native"] }),
      ]),
    ).toEqual(["React.js", "React Native"]);
  });

  it("does not match inside a longer word", () => {
    expect(marked("JavaScript", [term({ label: "Java", patterns: ["Java"] })])).toEqual([]);
    expect(marked("reaction", [term({ label: "React", patterns: ["React"] })])).toEqual([]);
  });

  it("respects case sensitivity for short names", () => {
    const terms = [term({ label: "Go", patterns: ["Go"], case_sensitive: true })];
    expect(marked("go fast", terms)).toEqual([]);
    expect(marked("Go fast", terms)).toEqual(["Go"]);
  });

  it("handles punctuation in skill names", () => {
    expect(
      marked("C++ and C# and .NET", [
        term({ label: "C++", patterns: ["C++"] }),
        term({ label: "C#", patterns: ["C#"] }),
        term({ label: ".NET", patterns: [".NET"] }),
      ]),
    ).toEqual(["C++", "C#", ".NET"]);
  });

  it("keeps repeated terms separate", () => {
    expect(marked("React, React, React", [term({ label: "React", patterns: ["React"] })])).toEqual([
      "React",
      "React",
      "React",
    ]);
  });

  it("does not match a case-sensitive term with different casing", () => {
    const segments = segmentText(
      "rest and REST",
      buildMatchGrammar([term({ label: "REST", patterns: ["REST"], case_sensitive: true })]),
    );
    expect(segments.filter((s) => s.term).map((s) => s.text)).toEqual(["REST"]);
  });

  it("honors blocked trailing phrases", () => {
    const segments = segmentText(
      "Go to market. Use Go daily.",
      buildMatchGrammar([
        term({
          label: "Go",
          patterns: ["Go"],
          case_sensitive: true,
          blocked_after: ["to"],
        }),
      ]),
    );
    expect(segments.filter((s) => s.term)).toHaveLength(1);
    expect(segments.find((s) => s.term)?.text).toBe("Go");
  });
});
