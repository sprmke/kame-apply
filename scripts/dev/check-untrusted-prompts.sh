#!/usr/bin/env bash
# Fail if AI call sites pass raw job description fields without going through safety.sanitize.
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
# Flag direct use of description_html/description_text inside ai/ prompt builders
# without an adjacent sanitize/for_ai_context import in the same file.
bad=0
while IFS= read -r -d '' f; do
  if grep -qE 'description_(html|text)' "$f" && ! grep -qE 'for_ai_context|sanitize_untrusted_' "$f"; then
    echo "untrusted-prompt: $f uses description_* without sanitize/for_ai_context"
    bad=1
  fi
done < <(find "$root/apps/api/app/ai" -name '*.py' -print0 2>/dev/null || true)
exit "$bad"
