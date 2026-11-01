# Route: `/profile/answers`

**Page:** `apps/web/app/pages/profile/answers.vue` · **Layout:** `default` · **Access:** signed in · `data.write` for edits

## Overview

Answer bank editor: quick setup, search, grouped keys, approve on save.

## API reference

| Call | Purpose |
| --- | --- |
| `GET .../answers`, `.../answers/keys` | list |
| `POST .../answers/setup` | seed defaults |
| `PATCH .../answers/{id}` | save text + approved |
