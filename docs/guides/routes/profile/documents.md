# Route: `/profile/documents`

**Page:** `apps/web/app/pages/profile/documents.vue` · **Layout:** `default` · **Access:** signed in

## Overview

Uploaded resumes and pastes. A short lede explains that parsed text must be reviewed before it becomes profile facts. Rows show a readable file size and status; Review opens parse review; Delete removes object + row.

## API reference

| Call | Purpose |
| --- | --- |
| `GET/POST .../documents` | list / upload |
| `DELETE .../documents/{id}` | delete |


## Portfolio photos

When the workspace's field pack enables portfolio images, **Add dish photo** accepts JPG, PNG, or WebP up to 10 MB for `kind=portfolio`. The server re-encodes the image to strip EXIF, GPS, and text chunks before storing it in R2. Other document kinds keep the PDF/DOCX/TXT/MD/JSON allowlist.
