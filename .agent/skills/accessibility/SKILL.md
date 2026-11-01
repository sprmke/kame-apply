---
name: accessibility
description: Framework-agnostic accessibility checklist for Kame Apply UI (forms, dialogs, focus, contrast, motion).
---

# Accessibility

- Semantic HTML first; ARIA only to fill gaps. Reka UI primitives handle dialog/menu/tabs semantics; do not reimplement focus traps.
- Every input has a visible label tied by `for`/`id`; errors are text plus `aria-describedby`, never color alone (risk levels: label + icon + color).
- Keyboard: every action reachable, visible focus ring (Field Notes focus token), logical order, Escape closes overlays, focus returns to the trigger.
- Touch targets at least 44x44px; no horizontal scroll at 375px.
- Contrast: WCAG AA at least for text and meaningful icons, in light and dark.
- Motion: honour `prefers-reduced-motion`; no motion that carries meaning alone.
- Live regions for async results (match scores updated, run state changes) with `aria-live="polite"`.
- Test with keyboard-only and a screen reader pass on forms and the Reader/Workbench layouts before closing a UI phase.
