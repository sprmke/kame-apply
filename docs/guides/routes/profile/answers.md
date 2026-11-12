# Route: `/profile/answers`

**Page:** `apps/web/app/pages/profile/answers.vue` · **Layout:** `default` · **Access:** signed in · `data.write` for edits

## Overview

Answer bank editor: a short lede explains that answers are reusable across applications and that Quick setup adds editable defaults. Search has an example placeholder, empty state explains the next step, and each answer saves with a quiet button.

## API reference

| Call | Purpose |
| --- | --- |
| `GET .../answers`, `.../answers/keys` | list |
| `POST .../answers/setup` | seed defaults |
| `PATCH .../answers/{id}` | save text + approved |


## UX clarity (2026-11-13)

**Draft my answers** calls `POST /profiles/{id}/answers/draft` and shows pencil cards with the source line ("From your profile", "A safe default", or "Answer this one yourself"). **Use this** creates the answer through the normal endpoint; **Dismiss** removes the card. Eligibility claims never arrive with a guessed answer.
