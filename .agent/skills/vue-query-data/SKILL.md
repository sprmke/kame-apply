---
name: vue-query-data
description: "Server state in the Nuxt app with Vue Query and the Hey API client: options, computed params, invalidation, optimistic updates."
---

# Vue Query data

- Use the generated query options from `packages/api-client` (Hey API + `@tanstack/vue-query`); never hand-write fetch calls for API endpoints. Regenerate after any API change.
- Reactive params: pass `computed` refs so queries refetch on change; give every query a stable key from the generated options.
- Mutations invalidate the narrowest keys that changed (list + detail), not the whole cache.
- Optimistic updates only for low-risk toggles (shortlist, dismiss, snooze) with rollback on error. Never optimistic for AI acceptance, status changes with side effects, or checkpoints.
- Errors: surface server `detail`; 401 triggers refresh once, then sign-out.
- Pinia is for UI state only. Server data is never copied into a store.
- Loading → skeletons shaped like the final content; empty → next step; error → what happened and what to do.
