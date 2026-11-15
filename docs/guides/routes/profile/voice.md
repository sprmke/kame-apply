# Route: `/profile/voice`

**Page:** `apps/web/app/pages/profile/voice.vue` · **Layout:** `default` · **Access:** signed in

## Overview

Paste 2 or 3 writing samples, analyze style, edit the summary, and maintain banned phrases. Samples have numbered labels and example placeholders. Copy states that samples guide tone only; facts still come from the profile.

## API reference

| Call | Purpose |
| --- | --- |
| `GET .../voice` | get or create |
| `PUT .../voice/samples` | replace + analyze |
| `PATCH .../voice` | summary / banned list |


## UX clarity (2026-11-13)

**Writing style** opens with three preset cards: Plain and direct (Recommended), Warm and human, Formal and precise. Choosing one calls `POST /profiles/{id}/voice/preset`. Samples stay optional and make the style more precise.
