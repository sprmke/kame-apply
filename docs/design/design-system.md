# Design system: "Field Notes"

**Status:** Proposed direction · **Last updated:** 2026-10-28 · Built in Phase 2, refined with the `impeccable` / `frontend-design` skills, then distilled into the repo-root `DESIGN.md`.

Kame Apply gets its **own** visual identity. It must not look like the other Kame apps. What those apps use, and what Kame Apply therefore avoids:

| Other Kame apps | Kame Apply |
| --- | --- |
| React + shadcn/Radix default look | Vue + Reka UI headless primitives with fully custom components |
| Teal (kame-homes), slate/teal/navy pilots (kame-desk) | Warm paper + ink neutrals, **persimmon** signal accent |
| Plus Jakarta Sans, IBM Plex | **Instrument Sans** (UI), **Newsreader** (documents), **Martian Mono** (data) |
| Lucide icons | **Phosphor** icons (regular + duotone) |
| Left sidebar + KPI tile grid dashboards | Slim rail + **Reader** three-pane + editorial **Today** brief |
| Divider rows / kanban as the core primitive | **Documents** with evidence marks, **route lines**, **dossiers** |

## 1. Concept

A job search is an expedition. You choose routes (Tracks), study the terrain (postings), keep field notes (your profile and evidence), and protect yourself (the shell: *kame* = turtle). The interface feels like a **well-kept field notebook in a calm operations room**: paper and ink for reading and writing, precise instruments for automation.

Three ideas run through every screen:

1. **Documents are the hero.** Job postings and resumes are typeset like good editorial pages; the app chrome recedes around them.
2. **Pencil vs ink.** Anything the AI drafted is shown in *pencil* (graphite tone, dashed underline, "draft" marker). Once the user accepts it, it turns to *ink*. This makes the draft-then-confirm principle visible everywhere.
3. **Every claim has a proof mark.** AI reasons, resume lines, filled fields, and risk flags carry a small evidence mark that reveals the source fact or posting quote.

## 2. Principles

1. **Read first, act second.** Layouts give the document the widest column; actions sit in a consistent context panel.
2. **Quiet automation, loud exceptions.** Background work is shown with calm instruments; only "Needs you" and danger use strong color and motion.
3. **Honest by design.** No fake precision ("ATS score 97%"), no dark patterns. Gaps and risks are shown as plainly as wins.
4. **Grayscale test.** Every screen must still read in grayscale: hierarchy comes from type, space, and rules, and color adds meaning.
5. **Two channels for meaning.** Status and risk always pair color with a glyph and a word.
6. **Phone-ready for decisions.** Triage, approvals, checkpoints, and live runs are fully usable at 375px.

## 3. Color (OKLCH tokens, Tailwind v4 `@theme`)

### Light ("Paper")

| Token | Value | Use |
| --- | --- | --- |
| `--paper-0` | `oklch(0.975 0.008 85)` | App background |
| `--paper-1` | `oklch(0.955 0.012 85)` | Raised surfaces, panels |
| `--paper-2` | `oklch(0.925 0.014 85)` | Sunken areas, table headers, wells |
| `--rule` | `oklch(0.86 0.015 85)` | Hairlines, borders |
| `--ink-900` | `oklch(0.22 0.01 70)` | Primary text |
| `--ink-600` | `oklch(0.45 0.012 70)` | Secondary text |
| `--ink-400` | `oklch(0.60 0.01 70)` | Tertiary, placeholders (never for essential info) |
| `--persimmon-500` | `oklch(0.66 0.18 40)` | Brand fills (with `ink-900` text), highlights, active route segment |
| `--persimmon-700` | `oklch(0.52 0.17 38)` | Accent text/links on paper, focus ring |
| `--pencil` | `oklch(0.50 0.03 280)` | AI draft text tint, dashed draft underline |
| `--fern-600` | `oklch(0.55 0.13 135)` | Safe / met / success |
| `--saffron-600` | `oklch(0.68 0.15 75)` | Caution / partial |
| `--oxblood-600` | `oklch(0.47 0.16 25)` | Danger / not met / destructive |
| `--track-*` | 8 muted hues at L≈0.62 C≈0.09 | Track identity (folder tabs, rail dots), never status |

### Dark ("Night desk")

`--paper-0 oklch(0.17 0.01 70)`, `--paper-1 oklch(0.21 0.012 70)`, `--paper-2 oklch(0.14 0.01 70)`, `--rule oklch(0.32 0.012 70)`, `--ink-900 oklch(0.93 0.01 85)`, `--ink-600 oklch(0.75 0.012 85)`, `--persimmon-500 oklch(0.72 0.16 45)`, `--persimmon-700 oklch(0.78 0.14 48)`, semantic hues raised to L≈0.72 for contrast. Warm, not blue-black.

### Rules

- Persimmon is the only brand color: one primary action per view, the active route segment, focus. Never as a background for large areas.
- Semantic colors (fern/saffron/oxblood) are reserved for risk, verdicts, and status. Never decorative.
- Contrast: body text ≥ 7:1, secondary ≥ 4.5:1, UI boundaries ≥ 3:1. CI checks the token pairs (script in Phase 2).
- No gradients, glassmorphism, glows, or pastel icon chips.

## 4. Typography

| Role | Font (free, Google Fonts) | Notes |
| --- | --- | --- |
| UI | **Instrument Sans** (variable) | Labels, controls, tables, navigation |
| Documents & display | **Newsreader** (variable, optical sizes) | Job postings, resumes preview, Today brief headlines, Lens grades, empty-state headings |
| Data | **Martian Mono** | Run logs, timestamps, IDs, counters in the live view. Small sizes only |

Scale (rem, 1.2 ratio for UI; documents use their own reading scale): `xs .75 · sm .8125 · base .875 (UI default) · md 1 · lg 1.2 · xl 1.44 · 2xl 1.728 · display 2.5`. Reading measure 64–72ch, line height 1.55 for documents. Tabular numerals for counts, money, dates in tables. Numbers in the Today brief use Newsreader lining figures.

## 5. Iconography and imagery

- **Phosphor** via Iconify (`@nuxt/icon`): Regular weight in UI, Duotone only in empty states and onboarding. 20px default, 16px dense.
- **Contour motif:** faint topographic contour lines (SVG, ≤ 6% opacity) only in the Today header, empty states, and the auth screens. It's the brand's texture.
- Logo direction: a hexagonal shell plate whose inner line forms a forward route arrow. Wordmark "Kame Apply" in Newsreader semibold.
- No stock illustrations or 3D blobs. Company logos are shown small and monochrome-tinted until hovered.

## 6. Shape, space, elevation

- Radius: `4px` inputs/chips, `8px` panels/sheets, `999px` only for the control pill and avatars.
- **Folder tab:** dossiers (applications) and Tracks have a small tab on the top-left edge in the Track color. It's the signature shape.
- Spacing scale 4px base: 4, 8, 12, 16, 24, 32, 48, 64. Density modes: **Comfortable** (reading, default) and **Compact** (tables; 32px rows).
- Elevation by rules and paper steps, not shadows. One soft shadow token only for floating layers (menus, sheets, command bar).

## 7. Signature components

| Component | Description |
| --- | --- |
| **Proof mark** | Inline dotted underline + tiny index superscript on any AI claim; hover/tap opens a popover with the source fact or posting quote and a link to it. |
| **Pencil text** | AI-drafted text: `--pencil` tint, dashed underline, "Draft" margin marker; Accept turns it to ink with a 200ms ink-fill transition. Used in resume diffs, answers, cover letters, status proposals. |
| **Fit ledger** | Qualification rows: glyph verdict (● met, ◐ partial, ○ not evidenced, ✕ knockout) + requirement + evidence proof mark + before→after column in tailoring. |
| **Route line** | A horizontal path with waypoints (found → shortlisted → tailored → applied → responded → interview → offer) replacing generic progress bars and kanban-only status. The active segment is persimmon, completed ones ink, future ones dotted. Used in tables (compact), dossiers (full), and the Today brief. |
| **Risk seal** | A stamp-like badge: icon + word (**Clear** / **Caution** / **Danger**) with semantic color; opens reasons with proof marks. |
| **Grade ring** | Lens grade as a Newsreader letter inside a thin ring; shows `C → A-` transitions with the delta. Labeled "simulation". |
| **Dossier** | The application detail: folder-tab header, route line, frozen posting, documents sent, answers, run replay, notes. |
| **Needs-you stack** | Prioritized action cards; on mobile a swipeable stack (resolve / snooze), on desktop a list in the Today brief and the rail badge. |
| **Live window** | Framed browser canvas with a control pill **AGENT ⇄ YOU**, a Martian Mono step log, and checkpoint banners. |
| **Command bar** | ⌘K global: jump to Track/job/application, run actions ("tailor for…", "run Track now"). |
| **Criteria chips** | Removable chips grouped under small-caps section labels, with a "compiled from your words" pencil diff after NL updates. |

## 8. Layout system

- **Rail** (desktop/tablet): a 64px vertical rail with icons for Today, Tracks, Jobs, Applications, Runs, Studio, Answer Desk, Safety, Settings, plus the Needs-you badge. Tracks open as a second-level **Track switcher** (folder tabs across the top of the content area), not a long sidebar list.
- **Reader** (three panes) for Jobs, Applications, and Studio: list (360px) · document (fluid, max 72ch) · context panel (360px: fit ledger, risk seal, actions). On tablet the context panel becomes a toggled overlay; on phone, list → document → context are a stacked navigation with a bottom action bar.
- **Brief** (Today): an editorial single column (max 880px) with a Newsreader headline summary ("6 strong new matches, 2 things need you"), the Needs-you stack, the route summary per Track, then the activity log.
- **Workbench** (Tailor, Resume Studio): document center with pencil diffs, ledger left, preview right (tabs on mobile).
- Mobile bottom bar: Today · Jobs · **Needs you** (center, shell-plate shaped button with count) · Applications · More.

## 9. Motion

"Steady pace": 160–220ms, ease-out `cubic-bezier(.2,.7,.2,1)`, no bounce or overshoot. Meaningful motion only: pencil → ink fill, route line advancing to its next waypoint, the Needs-you stack settling, live-window control handoff. `prefers-reduced-motion` turns all motion into instant state changes. Implemented with CSS transitions + Motion for Vue (`motion-v`) for list/route animations.

## 10. Data visualization

ECharts (via `vue-echarts`) with a custom theme: ink axes and labels in Instrument Sans, one persimmon emphasis series, others in ink tints; semantic colors only for risk/verdict charts. Every chart has a table view and a one-sentence takeaway in Newsreader. Follow the `dataviz` skill for accessibility.

## 11. Voice

Plain, warm, and direct, like a sharp friend who is good at hiring. Short labels; full sentences only in the Today brief and explanations. No hype, no AI clichés (shared banned-phrase list with the answer engine), no exclamation marks in system copy. Errors say what happened and what to do next.

## 12. Accessibility

WCAG 2.2 AA minimum. Focus ring: 2px `--persimmon-700` + 2px paper offset. Every glyph-only element has an accessible name. Proof-mark popovers are keyboard reachable (Enter/Escape). Live window has a text step log equivalent. Respect `prefers-contrast` with a high-contrast token set. Touch targets ≥ 44px.

## 13. Do / don't (enforced by `anti-slop-design` rule + design review)

**Do:** documents first, proof marks on every AI claim, pencil→ink for drafts, route lines for progress, one persimmon action per view.
**Don't:** teal or indigo accents, Lucide icons, shadcn default styles, KPI tile grids with icon chips, card-in-card, gradients, glow, confetti, emoji in UI chrome, AI sparkle icons for every AI feature (AI is shown by pencil text and proof marks, not sparkles).

## 14. Implementation notes

- Tokens live in `packages/ui/src/tokens.css` (`@theme`), shared by the Nuxt web app and the WXT extension.
- Components: Vue SFCs in `packages/ui` built on **Reka UI** primitives (dialog, popover, combobox, tabs, toast, tooltip...) + `tailwind-variants`; a living style guide route (`/_design`) renders every component and state in light/dark at three widths.
- Visual regression: Playwright screenshots of `/_design` per PR.
