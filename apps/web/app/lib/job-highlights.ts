export type MatchVerdict = "met" | "partial" | "gap";

export type MatchTerm = {
  key: string;
  label: string;
  patterns?: string[];
  blocked_after?: string[];
  verdict: MatchVerdict;
  mentions?: number;
  evidence?: string | null;
  case_sensitive?: boolean;
};

export type TextSegment = { text: string; term?: MatchTerm };

export type MatchGrammar = {
  regex: RegExp | null;
  termsByGroup: Map<string, MatchTerm>;
};

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/**
 * Build one alternation for every surface form, longest first, so "React.js"
 * wins over "React" and terms never match inside a longer word.
 */
export function buildMatchGrammar(terms: MatchTerm[] | null | undefined): MatchGrammar {
  const entries: { pattern: string; term: MatchTerm }[] = [];
  for (const term of terms ?? []) {
    const patterns = (term.patterns?.length ? term.patterns : [term.label]).filter(Boolean);
    for (const pattern of patterns) entries.push({ pattern, term });
  }
  if (!entries.length) return { regex: null, termsByGroup: new Map() };

  entries.sort((a, b) => b.pattern.length - a.pattern.length);
  const termsByGroup = new Map<string, MatchTerm>();
  const parts = entries.map((entry, index) => {
    const group = `t${index}`;
    termsByGroup.set(group, entry.term);
    const blocked = (entry.term.blocked_after ?? [])
      .map((word) => `(?!\\s+${escapeRegExp(word)}\\b)`)
      .join("");
    return `(?<${group}>(?<![\\p{L}\\p{N}_])${escapeRegExp(entry.pattern)}(?![\\p{L}\\p{N}_])${blocked})`;
  });

  return { regex: new RegExp(parts.join("|"), "giu"), termsByGroup };
}

function resolveTerm(match: RegExpMatchArray, grammar: MatchGrammar): MatchTerm | undefined {
  for (const [group, term] of grammar.termsByGroup) {
    if (match.groups?.[group] === undefined) continue;
    // Short names such as Go and React are case sensitive; reject other casings.
    if (term.case_sensitive) {
      const found = match.groups[group];
      if (!(term.patterns ?? [term.label]).includes(found)) return undefined;
    }
    return term;
  }
  return undefined;
}

/** Split text into plain runs and matched terms. Overlaps go to the longest pattern. */
export function segmentText(text: string, grammar: MatchGrammar | null | undefined): TextSegment[] {
  if (!text) return [];
  if (!grammar?.regex) return [{ text }];

  const out: TextSegment[] = [];
  let last = 0;
  for (const match of text.matchAll(grammar.regex)) {
    const index = match.index ?? 0;
    const term = resolveTerm(match, grammar);
    if (!term) continue;
    if (index > last) out.push({ text: text.slice(last, index) });
    out.push({ text: match[0], term });
    last = index + match[0].length;
  }
  if (last < text.length) out.push({ text: text.slice(last) });
  return out;
}
