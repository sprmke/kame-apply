# Route: `/profile/review/:documentId`

**Page:** `apps/web/app/pages/profile/review/[documentId].vue` · **Layout:** `default` · **Access:** signed in

## Overview

Side-by-side original extract and parsed draft. Parse, then confirm. If the profile already has facts, opens merge.

## API reference

| Call | Purpose |
| --- | --- |
| `POST .../parse` | LLM draft |
| `POST .../confirm` | apply to empty profile |
| `GET .../merge` | when `merge_required` |
