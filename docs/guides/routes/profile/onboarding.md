# Route: `/profile/onboarding`

**Page:** `apps/web/app/pages/profile/onboarding.vue` · **Layout:** `default` · **Access:** signed in

## Overview

First-run profile step: choose a resume file or paste text, then continue to parse review.

## Save path

Upload → `POST /api/v1/profiles/{id}/documents` → navigate to `/profile/review/{documentId}`.
