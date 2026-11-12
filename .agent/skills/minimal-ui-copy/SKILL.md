---
name: minimal-ui-copy
description: >-
  Clear and short UI copy. Keeps labels tight while allowing one section intro
  line, a field help tooltip, one consequence sentence, and one-line empty
  states, because a screen nobody understands is not minimal, it is unfinished.
  Use for every UI change in apps/web/**, apps/extension/**, new components,
  settings cards, forms, modals, and empty states.
---

# Minimal UI copy: clear and short

## Core rule

Do not add filler. Do add the one sentence a person needs to use the screen.

The test is not "fewer words". It is **would a careful person who has never seen this page know what it is for and what to do next?** If no, one short line is required, not optional.

## What is allowed

| Allowed | Limit | Where |
| --- | --- | --- |
| Section intro line | About 12 words, plain | Under a section title whose meaning is not obvious |
| Field help | 1 sentence | `?` tooltip on the label (`FnField` `help`) |
| Consequence or summary line | 1 sentence, generated from current values | End of a settings block, before an automatic action |
| Empty state | 1 line + 1 action (+ optional template picker) | Any empty list or panel |
| First-run hint | 1 line, dismissible, once per user | Patterns such as keyboard shortcuts or swipe |
| Explanation of a number | 1 sentence in a popover | Any score, count, or status |

## What stays banned

- Page or section subtitles that restate the title.
- Paragraphs, marketing, tutorial voice ("This lets you…", "Simply…").
- Helper text under every field. Use the `?` tooltip when help is genuinely needed.
- Em dashes, exclamation marks, emoji in chrome (see `human-copy`).
- Duplicating data already on screen.

## Patterns

### Section intro and summary

```vue
<!-- ❌ Bare title, no clue what the block does -->
<h2>Autonomy</h2>

<!-- ✅ Plain title, one line, one consequence line at the end -->
<FnSectionCard
  title="How much we do"
  intro="How far we go on each match before we stop for you."
  :summary="`We find and score jobs, then draft a resume for the ones you shortlist. Nothing is sent.`"
>
```

### Field help

```vue
<!-- ❌ Helper paragraph under the field -->
<FnField label="Minimum match" hint="Only jobs scoring at least this high are considered." />

<!-- ✅ One sentence behind a ? on the label -->
<FnField label="Minimum match" help="Only jobs scoring at least this high are considered." />
```

### Page header

```vue
<!-- ❌ Subtitle repeats the title -->
<PageHeader title="Applications" lede="View all the jobs you have applied to." />

<!-- ✅ Title only; the table and statuses carry the meaning -->
<PageHeader title="Applications" />
```

### Empty state

```vue
<!-- ❌ Essay -->
<FnEmptyState title="No searches yet" body="A search is a saved role that we check..." />

<!-- ✅ One line, one action -->
<FnEmptyState title="No searches yet" body="Start with the role you want." action="New search" />
```

## Before shipping a string

1. Does the screen pass the first-glance test without it? If yes, cut it.
2. Is it longer than the limit in the table above? Cut 30%.
3. Does it use a barely-known internal word? Replace it with the glossary word (`docs/design/glossary.md`).
4. Does it contain an em dash or a banned word? Rewrite (`human-copy`).

## Refactors

When touching a file, replace bare internal section titles with plain ones plus at most one intro line. Do not expand existing copy into paragraphs. Remove descriptions that restate the title.

## Related

- Rule: `.cursor/rules/ui-minimal-copy.mdc`
- `human-copy`: how the text must sound
- `docs/design/glossary.md`: the words to use
- `ux-clarity-review`: checks the five first-glance questions on a route
- `accessibility`: labels, focus, and target size
