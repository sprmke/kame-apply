# Design: Field Notes

Distilled from `docs/design/design-system.md` and implemented in `packages/ui` (Phase 2). The living style guide is `/_design`; tokens are `packages/ui/src/tokens.css`. If this file and the design system disagree, fix the one that is wrong in the same change.

**Concept:** paper and ink for reading and writing, precise instruments for automation. Three ideas on every screen: documents are the hero; pencil vs ink (AI drafts vs accepted text); every claim has a proof mark.

**Color (OKLCH, Tailwind v4 `@theme`):** paper neutrals (`paper-0/1/2`, `rule`), `edge` for control borders (3:1), ink text (`ink-900/600/400`), one brand accent **persimmon** (`500` fills with `on-brand` text, `700` for text and focus), `pencil` for AI drafts, semantic `fern/saffron/oxblood-600` for safe, caution, danger only, eight muted `track-1..8` hues for Track identity (never status). Dark is warm "Night desk", not blue-black. A high-contrast set applies under `prefers-contrast: more`. `pnpm run check:token-contrast` enforces the pairs; change a token only with that check green. No gradients, glass, glows, or pastel icon chips.

**Type:** Instrument Sans (UI, 14px base), Newsreader (documents, display, brief headlines), Martian Mono (data, logs, small). Scale tokens `--text-xs` to `--text-display`. Documents: 64 to 72ch, line height 1.55. Tabular numerals in tables.

**Icons:** Phosphor via `@nuxt/icon` (`ph:` names), Regular in UI. No Lucide, no sparkles for AI. Glyph-only controls need an accessible name.

**Shape and space:** radius 4 (inputs, chips) and 8 (panels, sheets); pill only for avatars. Spacing on a 4px base. Elevation by rules and paper steps; one `--shadow-float` for floating layers. Folder tab for Tracks and dossiers.

**Layouts:** Rail (64px) with the Needs-you badge, top bar (workspace switcher, command bar, profile), phone bottom bar (Today, Jobs, centre Needs-you plate, Applications, More). Reader, Brief (Today, max 880px) and Workbench primitives follow as screens arrive.

**Components (`packages/ui`, prefix `Fn`):** Button, Input, Textarea, Field (label, hint, error, aria wiring), Checkbox, Select, Chip, Tabs, Dialog (also the sheet), Popover, Tooltip, Menu, Toaster (`useToast`), CommandBar, Table, Skeleton; signature: ProofMark, PencilText, RouteLine, RiskSeal, GradeRing, FolderTab. Built on Reka UI with `tailwind-variants`. They carry no language: strings arrive as props or slots.

**Motion:** 160 to 220ms, `cubic-bezier(.2,.7,.2,1)`, no bounce, meaningful only, honors `prefers-reduced-motion` (`--dur-steady: 0ms`).

**Voice:** plain, warm, direct. No hype, no exclamation marks, no em dashes; errors say what happened and what to do. Strings live in the catalog.

**Accessibility:** WCAG 2.2 AA, 44px targets, two channels for meaning (color plus glyph plus word), visible 2px persimmon focus ring, skip link, keyboard-reachable overlays, tables have captions, charts have a table view.

**Never:** another Kame app's tokens, components or look; teal or indigo accents; KPI tile grids; card-in-card; emoji in chrome.
