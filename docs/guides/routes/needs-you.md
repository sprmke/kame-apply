# Route: `/needs-you`

**Page:** `apps/web/app/pages/needs-you.vue` · **Layout:** `default` · **Access:** signed in · `data.read`

## Progress overview

| Section | E2E | Validation | Docs | Notes |
| --- | --- | --- | --- | --- |
| Decision list | Done | n/a | Documented | Polls every 20 seconds |
| Empty state | Done | n/a | Documented | One line plus Browse jobs |

## Behavior

The decisions waiting on the user: open apply checkpoints, tailored drafts ready to review, and safety decisions. Each row links straight to the screen that resolves it. Items are deduplicated by kind and link so two runs finishing together do not show twice.

The shell badge counts the same source. `/notifications` remains the event inbox.

Common questions:

- **Why did this appear?** A run stopped at a checkpoint, or a draft is ready for review.
- **What if I ignore it?** It stays here; nothing is submitted without the decision.

## Implementation map

`needs-you.vue`, `GET /api/v1/needs-you`, i18n `needsYou.*`.
