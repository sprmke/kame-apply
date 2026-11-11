# Design system: Signal

**Status:** Current · **Last updated:** 2026-11-12 · Replaces Field Notes. Built on the repo-root `DESIGN.md` and implemented in `packages/ui/src/tokens.css`.

Kame Apply has its own visual identity. It must not look like the other Kame apps. Signal is a calm job-search workspace: one typeface, a cool canvas, white surfaces, one indigo brand, and soft elevation. Documents and decisions get the space; chrome recedes.

| Other Kame apps | Kame Apply (Signal) |
| --- | --- |
| React + shadcn/Radix default look | Vue + Reka UI headless primitives with custom components |
| Teal (kame-homes), slate/teal/navy pilots (kame-desk) | Cool gray canvas, white cards, **indigo** brand |
| Plus Jakarta Sans, IBM Plex | **Manrope** for UI, display, documents, and data |
| Lucide icons | **Phosphor** icons (regular; duotone only in empty states) |
| Left sidebar + KPI tile grid dashboards | 240px labeled sidebar + **Reader** three-pane + **Brief** |
| Divider rows / kanban as the core primitive | Documents with evidence marks, route lines, dossiers |

## 1. Concept

A job search is a series of decisions, not a dashboard to admire. The interface should feel like a clear workspace: the posting and the resume are the documents; the shell is quiet; the next action is obvious.

Three ideas run through every screen:

1. **Documents are the hero.** Job postings and resumes get the widest column and the calmest surface.
2. **Pencil vs ink.** Anything the AI drafted is shown in *pencil*. Once the user accepts it, it turns to *ink*. This makes draft-then-confirm visible.
3. **Every claim has a proof mark.** AI reasons, resume lines, filled fields, and risk flags carry an evidence mark that reveals the source fact or posting quote.

## 2. Principles

1. **One next action.** Every view has one primary action, styled as a filled indigo button, never a link.
2. **Read first, act second.** The document gets the space; actions sit in a consistent context panel or sticky bar.
3. **Quiet automation, loud exceptions.** Background work is calm; only "Needs you" and danger use strong color and motion.
4. **Honest by design.** No fake precision, no dark patterns. Gaps and risks are as plain as wins.
5. **Grayscale test.** Every screen reads in grayscale. Hierarchy comes from type, space, and rules; color adds meaning.
6. **Two channels for meaning.** Status and risk always pair color with a glyph and a word.
7. **Phone-ready for decisions.** Triage, approvals, checkpoints, and live runs work at 375px.
8. **44px minimum.** Every interactive target is at least 44px tall.

## 3. Color (OKLCH tokens, Tailwind v4 `@theme`)

### Light

| Token | Value | Use |
| --- | --- | --- |
| `--paper-0` | `oklch(0.975 0.006 255)` | App canvas |
| `--paper-1` | `oklch(1 0 0)` | Cards, header, sidebar |
| `--paper-2` | `oklch(0.95 0.008 255)` | Table heads, tab tracks, recessed areas |
| `--rule` | `oklch(0.9 0.008 255)` | Hairlines, card borders |
| `--edge` | `oklch(0.62 0.015 255)` | Control borders (3:1) |
| `--ink-900` | `oklch(0.22 0.02 255)` | Primary text |
| `--ink-600` | `oklch(0.45 0.02 255)` | Secondary text |
| `--ink-400` | `oklch(0.58 0.015 255)` | Metadata, placeholders |
| `--brand-50` | `oklch(0.96 0.02 275)` | Soft brand surface |
| `--brand-100` | `oklch(0.92 0.04 275)` | Focus ring, selected row |
| `--brand-200` | `oklch(0.86 0.07 275)` | Brand border |
| `--brand-500` | `oklch(0.48 0.2 275)` | Primary fill |
| `--brand-600` | `oklch(0.43 0.2 275)` | Primary hover |
| `--brand-700` | `oklch(0.37 0.18 275)` | Brand text, links, active nav |
| `--on-brand` | `oklch(0.99 0 0)` | Text on brand fills |
| `--pencil` | `oklch(0.5 0.12 300)` | AI drafts and unaccepted text |
| `--fern-600` | `oklch(0.5 0.13 155)` | Safe / met / success |
| `--saffron-600` | `oklch(0.55 0.13 75)` | Caution / partial |
| `--oxblood-600` | `oklch(0.47 0.16 25)` | Danger / destructive |
| `--track-1..8` | 8 muted hues at L≈0.55 C≈0.09 | Search identity. Never status. |

### Dark

Cool, not blue-black. `--paper-0 oklch(0.16 0.012 255)`, `--paper-1 oklch(0.2 0.014 255)`, `--paper-2 oklch(0.24 0.016 255)`, `--rule oklch(0.32 0.012 255)`, `--ink-900 oklch(0.96 0.006 255)`, `--brand-500 oklch(0.72 0.16 275)`, `--on-brand oklch(0.16 0.012 255)`. Semantic hues are raised to L≈0.72 for contrast. High-contrast theme raises rules and text further.

### Rules

- One brand fill per view: the primary action. Active nav and focus use brand text or a brand-50 surface, not a second filled button.
- Semantic colors are reserved for risk, verdicts, and status. Never decorative.
- Contrast: body text ≥ 7:1, secondary ≥ 4.5:1, UI boundaries ≥ 3:1. `scripts/dev/check-token-contrast.mjs` checks 29 pairs across 4 themes.
- No gradients, glassmorphism, glows, or pastel icon chips.

## 4. Typography

| Role | Font (free, Google Fonts) | Notes |
| --- | --- | --- |
| Everything | **Manrope** (variable, 400 to 800) | UI, display, documents, data |

Scale (rem, 16px base): `xs .75 · sm .875 · base 1 · md 1.125 · lg 1.25 · xl 1.5 · 2xl 1.875 · display 3`. Page titles are 30 to 36px, bold, tracking -0.03em. Today's display is 48px. Reading measure 64 to 72ch; line height 1.55 for documents. Data uses tabular numerals, not a second mono typeface. No tiny mono labels.

## 5. Iconography and imagery

- **Phosphor** via Iconify (`@nuxt/icon`): Regular weight in UI, Duotone only in empty states and onboarding. 20px default, 16px dense.
- **No decorative texture.** Signal does not use the old contour motif. A brand-50 surface is enough.
- **No stock illustrations, 3D blobs, or generic hero art.** Use the real document, the real match list, or a short empty state.
- **No emoji in chrome.** Status uses glyphs from Phosphor plus a word.

## 6. Shape and elevation

- Radius: 8px controls, 12px cards, 16px panels, 24px dialogs.
- Cards: `bg-paper-1`, `border-rule`, `rounded-xl`, `shadow-[var(--shadow-card)]`.
- Floating layers: `shadow-[var(--shadow-float)]`.
- Buttons: `shadow-[var(--shadow-button)]` on primary only.
- No nested cards. A card inside a card is a section that should be a row or a plain surface.

## 7. Components

`packages/ui` with the `Fn` prefix: Button, Input, Textarea, Field, Checkbox, Select, Chip, Tabs, Dialog, Popover, Tooltip, Menu, Toaster, CommandBar, Table, Skeleton; signature: ProofMark, PencilText, RouteLine, RiskSeal, GradeRing, FolderTab.

- **Button:** primary (indigo fill, white text), quiet (white surface, rule border, shadow), ghost (text, hover paper-2), danger (oxblood text and border). Sizes: 44px sm, 48px md, 56px lg.
- **Input / Textarea / Select:** 44px minimum, white surface, rule border, 2px brand focus ring with a brand-100 halo.
- **Tabs:** a `paper-2` track with a white active pill and brand-700 text. Never underline-only.
- **Table:** recessed `paper-2` header, 56px rows, tabular numerals, hover `paper-2`.
- **Dialog:** 24px radius, `shadow-float`, 44px close control.
- **Empty state:** short title, one line, one action. A dashed card only when the surface has no data at all.
- **Cards:** white surfaces. Do not put a bordered card inside another card.

## 8. Layouts

- **Desk sidebar** (240px): Today, Searches, Jobs, Applications, Profile. More tools collapsed. Settings at the bottom. Labels always visible. Active item is a brand-50 pill with brand-700 text.
- **Header** (64px): workspace switcher, search, account. No feedback button in the primary chrome.
- **Reader:** list, document, context. Desktop three panes inside one card. Mobile: list, then full-screen document with a sticky action bar above the tab bar.
- **Brief:** Today, max 1040px. One next step, top matches, searches, Needs-you. Numbers in a collapsed disclosure.
- **Workbench:** resume and tailor. Document center, ledger, preview.
- **Mobile bar:** Today, Searches, Jobs, Applications, More. 64px. Active tab brand-700, label always visible.
- **Settings:** horizontal tab track; one row scrolls on mobile, wraps on desktop. Content sits in one white card.

## 9. Motion

160 to 220ms, `cubic-bezier(.2,.7,.2,1)`, no bounce. Meaningful only: pencil to ink, route line advance, Needs-you settle, live handoff. Honor `prefers-reduced-motion` (the token duration becomes 0ms).

## 10. Copy and voice

Plain, warm, direct. Short labels. No hype, exclamation marks, or em dashes. Errors say what happened and what to do next. No tutor voice. Labels are 1 to 4 words; buttons 1 to 3. AI output is a draft until accepted.

## 11. Accessibility

WCAG 2.2 AA. 44px targets. Visible 2px brand focus ring. Two channels for meaning. Skip link. Keyboard-reachable overlays. Tables have captions. Charts have a table view. Test at 375, 820, and 1440 in light and dark. Visual audit: `pnpm run audit:ui`.

## 12. Do and don't

**Do**

- Give the document the widest column.
- Use one primary button per view.
- Use `FnButton`, `FnInput`, card surfaces, and the tokens.
- Keep the sidebar labels visible and the active item clear.
- Use a short empty state with one action.

**Don't**

- Use another Kame app's tokens, components, or look.
- Use gradients, glass, glow, or decorative blur.
- Use KPI tile grids, card-in-card, or emoji in chrome.
- Use a second typeface, tiny mono labels, or 32px buttons.
- Use sparkles for AI. Use pencil text and proof marks.
- Use color alone for status.
- Truncate job titles, company names, errors, or primary labels.
