---
name: route-guides
description: >-
  Create or update per-route operator guides in docs/guides/routes when
  implementing or changing pages, sections, or features. REQUIRED for every
  route/page/section UX change — use before claiming done. Also use when
  touching UI routes, page behavior, save flows, validation, or when the user
  mentions route guides, docs/guides, or page documentation. Pairs with
  documentation-maintenance.
---

# Route guides skill

Living per-page specs live in **`docs/guides/routes/`**, aligned with app URLs. Update them in the same PR/session as code changes.

## When to use

- Adding or changing a **page**, **section**, or **feature** with user-visible behavior
- Changing **save paths**, **validation**, **API calls**, or **permissions** on a screen
- User asks to document a route or section

Skip for trivial fixes (typos, rename-only refactors).

## Workflow

1. **Identify the route** — read the page under `apps/web/pages/` (or the extension entrypoint under `apps/extension/entrypoints/`).
2. **Open or create the guide** — path mirrors URL (see **Route → file mapping** below).
3. **Read existing guide** — preserve accurate content; edit in place.
4. **Implement code change.**
5. **Update the guide** — behavior, validation, save paths, API table, implementation map, **User-facing knowledge**, progress table.
6. **Update index** — `docs/guides/routes/README.md` link/status if new route or first real doc.
7. **Cross-check** — `docs/architecture/` for API/env; link `.cursor/rules/` for canonical workflow/auth rules instead of copying matrices.

## Route → file mapping

**Single source of truth:** [`docs/guides/routes/README.md`](../../../docs/guides/routes/README.md).

Do **not** maintain a duplicate route→file table in this skill. Look up the guide path and status in the README index. New route: copy **`docs/guides/_template.md`**, place under matching URL path segments (omit dynamic params like `:orgSlug`), add a README row.

## Guide template (sections)

Use **`docs/guides/_template.md`**. Every documented page should include:

| Section                   | Content                                                                  |
| ------------------------- | ------------------------------------------------------------------------ |
| **Progress overview**     | Table: Section \| E2E \| Validation \| Docs \| Notes                     |
| **Overview**              | One short paragraph — who uses it, what it does                          |
| **User-facing knowledge** | Plain-language summary + **Common user questions** Q&A (see rules below) |
| **Sections**              | One `##` per UI section — fields, storage, validation, save path         |
| **API reference**         | API endpoints + key request/response notes                              |
| **Implementation map**    | Page component, hooks, shared modules, API endpoints                    |
| **Related docs**          | Links to the architecture doc and canonical rules as needed              |
| **Pending / follow-ups**  | Checkbox list for known gaps                                             |

**Example:** the first completed guide becomes the reference (Phase 2 sets the template at `docs/guides/_template.md`).

## Writing rules

- **Behavior over code dump** — describe what happens, not every line.
- **Tables for fields/API** — field name, storage column/JSON path, validation rule.
- **Save path numbered steps** — UI action → endpoint → DB/storage side effects.
- **Link canonical rules** — checkpoint/run behavior → `apply-engine.mdc`; tenancy → `workspace-scoping.mdc`; auth → `fastapi-jwt-auth` skill.
- **Keep UI/API validation in sync** — note both paths when rules are duplicated (see settings guide).
- **Minimal copy in guides is OK** — precise ops language, not marketing text.
- **User-facing knowledge** — plain language only. No code, no DB column names, no internal endpoint/file paths. Write Q&A a user could read in help text (or platform operator for `/admin/*`).

## Progress table values

| Column     | Values                               |
| ---------- | ------------------------------------ |
| E2E save   | `Done` · `Partial` · `—` · `N/A`     |
| Validation | `Done` · `Partial` · `—`             |
| Docs       | `Done` · `Pending`                   |
| Notes      | Short caveat (e.g. "upload-only QR") |

## Checklist before finishing

- [ ] Guide path matches route
- [ ] Progress table reflects current sections
- [ ] **User-facing knowledge** present (plain language, no technical leakage)
- [ ] New/changed fields, endpoints, and validations documented
- [ ] Implementation map paths exist in repo
- [ ] `docs/guides/routes/README.md` updated if new route
- [ ] `docs/PROJECT.md` updated if API/env/architecture changed (per `documentation-maintenance.mdc`)
