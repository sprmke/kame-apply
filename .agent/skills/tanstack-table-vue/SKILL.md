---
name: tanstack-table-vue
description: Virtualized lists/tables in Vue with TanStack Table + Virtual for the Reader list panes.
---

# TanStack Table (Vue)

- `@tanstack/vue-table` for column logic, `@tanstack/vue-virtual` for rows; 32px compact rows, comfortable density by default.
- Server-side sorting/filtering/pagination for job lists (cursor-based); the table only renders what the API returns.
- Keyboard: arrow keys move selection, Enter opens the document pane, Space toggles shortlist; selection is announced to screen readers.
- Row anatomy: title and company never truncate (anti-slop H6), route line compact, risk seal, fit glyphs; tabular numerals.
- Persist column visibility and density per user via the settings API, not localStorage alone.
