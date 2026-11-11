# Design: Signal

Signal is the current design system. It replaces Field Notes. The product should feel calm, confident, and human: a clear job-search workspace, not a developer dashboard.

**Concept:** one typeface, a cool canvas, white surfaces, one indigo brand, and soft elevation. Documents and decisions get the space; chrome recedes. Every screen has one obvious next action.

## Color

Tokens live in `packages/ui/src/tokens.css`. Use classes, never raw colors.

| Token                                      | Role                                      |
| ------------------------------------------ | ----------------------------------------- |
| `paper-0`                                  | Canvas                                    |
| `paper-1`                                  | Surface, cards, sidebar, header           |
| `paper-2`                                  | Recessed surface, table heads, tab tracks |
| `rule`                                     | Borders and separators                    |
| `edge`                                     | Control borders (3:1)                     |
| `ink-900` / `ink-600` / `ink-400`          | Primary, secondary, metadata text         |
| `brand-500`                                | Primary action fill                       |
| `brand-600`                                | Primary hover                             |
| `brand-700`                                | Brand text, links, active nav             |
| `brand-50` / `brand-100` / `brand-200`     | Soft brand surfaces, focus rings, borders |
| `on-brand`                                 | Text on brand fills                       |
| `pencil`                                   | AI drafts and unaccepted text             |
| `fern-600` / `saffron-600` / `oxblood-600` | Safe, caution, danger only                |
| `track-1..8`                               | Search identity. Never status.            |

One brand fill per view. Status always uses color, glyph, and word.

## Type

One family: **Manrope**, weights 400 to 800. Headings are bold with tight tracking. UI copy is 16px. Data uses tabular numerals, not a second mono typeface.

| Role            | Size                               |
| --------------- | ---------------------------------- |
| Page title      | 30 to 36px, bold, tracking -0.03em |
| Section title   | 18 to 20px, bold                   |
| Body            | 16px                               |
| Secondary       | 14px                               |
| Metadata        | 12 to 13px                         |
| Display (Today) | 48px                               |

## Shape and elevation

- Radius: 8px controls, 12px cards, 16px panels, 24px dialogs.
- Cards: `bg-paper-1`, `border-rule`, `rounded-xl`, `shadow-[var(--shadow-card)]`.
- Floating layers: `shadow-[var(--shadow-float)]`.
- No gradients, glass, glow, or decorative blur.

## Buttons

- **Primary:** indigo fill, white text, semibold, 48px default height, soft shadow, hover darker.
- **Secondary:** white surface, rule border, ink text, soft shadow.
- **Ghost:** text only, hover paper-2.
- **Danger:** oxblood text and border.
- All controls are at least 44px tall. No 32px buttons.
- One primary action per view. The primary action is a filled button, not a link.

## Layouts

- **Desk sidebar** (240px): Today, Searches, Jobs, Applications, Profile. More tools collapsed. Settings at the bottom. Labels always visible.
- **Header** (64px): workspace switcher, search, account. No feedback button in the primary chrome.
- **Reader:** list, document, context. On mobile: list, then full-screen document with a sticky action bar.
- **Brief:** Today, max 1040px. One next step, top matches, searches, Needs-you. Numbers in a collapsed disclosure.
- **Workbench:** resume and tailor. Document center, ledger, preview.
- **Mobile bar:** Today, Searches, Jobs, Applications, More. 64px. Active tab in brand-700.

## Components

`packages/ui` with `Fn` prefix: Button, Input, Textarea, Field, Checkbox, Select, Chip, Tabs, Dialog, Popover, Tooltip, Menu, Toaster, CommandBar, Table, Skeleton; signature: ProofMark, PencilText, RouteLine, RiskSeal, GradeRing, FolderTab.

- Cards are white surfaces, not outlined boxes inside other boxes.
- Tables use a recessed header and 56px rows.
- Empty states use a short title, one line, and one action.
- Dialogs are 24px radius with a 44px close control.

## Motion

160 to 220ms, `cubic-bezier(.2,.7,.2,1)`, no bounce. Meaningful only: pencil to ink, route line advance, Needs-you settle, live handoff. Honor `prefers-reduced-motion`.

## Voice

Plain, warm, direct. Short labels. No hype, exclamation marks, or em dashes. Errors say what happened and what to do next. No tutor voice.

## Accessibility

WCAG 2.2 AA. 44px targets. Visible 2px brand focus ring. Two channels for meaning. Skip link. Keyboard-reachable overlays. Tables have captions. Charts have a table view. Test at 375, 820, and 1440.

## Never

- Another Kame app's tokens, components, or look.
- Gradients, glass, glow, or pastel icon chips.
- KPI tile grids, card-in-card, or emoji in chrome.
- A second typeface, tiny mono labels, or 32px buttons.
- Sparkles for AI. Use pencil text and proof marks.
