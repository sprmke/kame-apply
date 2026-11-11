# Route: `/profile/documents`

**Page:** `apps/web/app/pages/profile/documents.vue` · **Layout:** `default` · **Access:** signed in

## Overview

Uploaded resumes and pastes. A short lede explains that parsed text must be reviewed before it becomes profile facts. Rows show a readable file size and status; Review opens parse review; Delete removes object + row.

## API reference

| Call | Purpose |
| --- | --- |
| `GET/POST .../documents` | list / upload |
| `DELETE .../documents/{id}` | delete |
