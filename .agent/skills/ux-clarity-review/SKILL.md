---
name: ux-clarity-review
description: >-
  Pass/fail clarity review of a Kame Apply route. Answers the five first-glance
  questions from screenshots, checks plain words, defaults, AI-assist patterns,
  and required states, then reports at most six issues with the one fix that
  matters most. Use before shipping a page, after a UX change, or via
  /ka-ux-review. Pairs with design-review (visual) and accessibility.
---

# UX clarity review

Default to flagging. A screen that needs an explanation has failed, and the reviewer's job is to say which line is missing or wrong.

This skill answers a different question from `design-review`. Design review asks "is this well made?". Clarity review asks **"would a first-time, non-technical person know where they are, what this is for, and what to do next?"** Run both when both matter.

## Read first

1. `docs/design/glossary.md` (the user words)
2. `docs/workflow/planned/ux-clarity-overhaul.md` §3 (the five questions), §7 (defaults), §6 (AI assists)
3. The route guide in `docs/guides/routes/`
4. `.cursor/rules/ui-minimal-copy.mdc` and `human-copy.mdc`

## Operating loop

1. **Capture.** Get screenshots of the real route at 375, 820, and 1440 in light and dark. If the app is running at `localhost:3100`, use the Playwright MCP tools (navigate, resize, screenshot) or `pnpm run capture:design-screenshots`. Save under `.audit-screenshots/reviews/<route>-<width>.png` (gitignored). Never review from code alone; never review from screenshots alone.
2. **Deterministic sweep.** Run `pnpm run check:ux-jargon`. Record every hit that belongs to this route.
3. **Five questions per section.** For each section on the screen, answer from the screenshot alone:
   - Where am I? Title says the thing in user words.
   - What is this for? One short line or an obvious visual.
   - What do I do next? Exactly one primary action is visually dominant.
   - What happens if I click it? The button is verb + object; automatic or irreversible actions show a consequence line.
   - Is anything waiting on me? Needs-you items are visible without hunting.
   Fail any one and the section fails.
4. **Words.** Every noun matches the glossary. No internal term is left unexplained. Buttons keep one name through the flow.
5. **Defaults.** Every control starts on a sensible value. A choice that matters is marked Recommended. A multi-field form offers a template or an AI draft before a blank field.
6. **AI assist pattern.** Each assist produces pencil text with Use / Edit / Discard, shows where facts came from, and has a non-AI path. A screen that only works with an AI key fails.
7. **States.** Empty, loading, error, partial, and permission-limited each exist and each says what to do. Check a cold account, not only the seeded one.
8. **Report.**

## Report format

- One line per section: `pass` / `fail` / `partial` / `not applicable` / `cannot tell from this artifact`.
- At most **six** issues, ranked by user impact. No padding.
- Each issue: **Before** (a fact from the screenshot or the string), **After** (one concrete change, doable in an hour), **Why** (a rule ID from the plan, a glossary row, or a WCAG SC).
- End with **the one fix that matters most**.
- If a screen genuinely passes, say so and add two polish items; never an empty pass.

## Rule IDs

- **Q1** where am I · **Q2** what is this for · **Q3** what do I do next · **Q4** what happens if I click · **Q5** anything waiting on me
- **W1** internal word · **W2** two names for one thing · **W3** missing consequence line
- **D1** no default · **D2** no template or draft path · **D3** setting with no summary sentence
- **A1** AI has no fallback · **A2** draft is not pencil · **A3** no evidence shown
- **S1** missing empty state · **S2** missing error state · **S3** mobile action unreachable · **S4** target under 44px

## Responsive gate (part of Q3)

At 375: the primary action is visible without horizontal scroll; the bottom bar does not cover it; tables become cards or scroll with a visible cue; the page has one column; type does not go below 12px; no element overflows the viewport. At 820: two-pane layouts fold without orphaned whitespace. At 1440: content has a max width and does not stretch into unreadable lines. Record the width in every issue that only fails at one size.

## Output

Write the report to `docs/design/previews/_reviews/<route-slug>.md` when the user asked for a durable review; otherwise return it in the reply. Update the route guide only when the fix lands.
