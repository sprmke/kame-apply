#!/usr/bin/env bash
# Plain-bash unit checks for the Claude Code hooks: feed sample inputs, assert allow/deny/ask.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
command -v jq >/dev/null || { echo "jq required"; exit 1; }
FAIL=0
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

shell_decision() {
  printf '%s' "$1" | jq -Rs '{tool_input:{command:.}}' | bash .claude/hooks/guard-shell.sh | jq -r '.hookSpecificOutput.permissionDecision // "allow"'
}
expect_shell() { # command expected
  local got; got="$(shell_decision "$1")"
  [[ "$got" == "$2" ]] || { echo "FAIL guard-shell: '$1' → $got (want $2)"; FAIL=1; }
}

# Built indirectly so this file itself never contains the literal destructive string.
DANGEROUS_RM="r""m -rf ~"

expect_shell "pnpm run deploy:api:prod" deny
expect_shell "pnpm run deploy:web:prod" deny
expect_shell "pnpm run migrate:prod" deny
expect_shell "pnpm run rollback:db:prod" deny
expect_shell "APPLYWAVE=applywave pnpm run deploy:api:prod" allow
expect_shell "pnpm run deploy:api:dev" allow
expect_shell "pnpm run db:migrate" allow
expect_shell "uv run alembic upgrade head --db-url postgresql://u:p@db.example.com/x" deny
expect_shell "uv run alembic upgrade head --db-url postgresql://u:p@db.neon.tech:5432/x" deny
expect_shell "uv run alembic upgrade head --db-url postgresql://u:p@127.0.0.1:5442/kame_apply" allow
expect_shell "git push --force origin main" deny
expect_shell "git push -f origin feature/x" ask
expect_shell "echo SECRET=1 > .env.production" deny
expect_shell "$DANGEROUS_RM" deny
expect_shell "psql -c 'DROP TABLE jobs'" ask
expect_shell "git status" allow

# check-stack-terminology: evasion must exit 2, clean file must exit 0
mkdir -p "$TMP/apps/api"
printf 'import playwright_stealth\n' > "$TMP/apps/api/bad.py"
printf 'import httpx\n' > "$TMP/apps/api/good.py"
for pair in "bad.py:2" "good.py:0"; do
  f="${pair%%:*}"; want="${pair##*:}"
  printf '{"tool_input":{"file_path":"%s"}}' "$TMP/apps/api/$f" | bash .claude/hooks/check-stack-terminology.sh >/dev/null 2>&1
  got=$?
  [[ "$got" == "$want" ]] || { echo "FAIL check-stack-terminology: $f exit $got (want $want)"; FAIL=1; }
done

# guard-shipped-migrations: existing file under versions/ denied, new path allowed
mkdir -p "$TMP/apps/api/migrations/versions"; : > "$TMP/apps/api/migrations/versions/0001_x.py"
got=$(printf '{"tool_input":{"file_path":"%s"}}' "$TMP/apps/api/migrations/versions/0001_x.py" | bash .claude/hooks/guard-shipped-migrations.sh | jq -r '.hookSpecificOutput.permissionDecision // "allow"')
[[ "$got" == deny ]] || { echo "FAIL guard-shipped-migrations: existing → $got"; FAIL=1; }
got=$(printf '{"tool_input":{"file_path":"%s"}}' "$TMP/apps/api/migrations/versions/0002_new.py" | bash .claude/hooks/guard-shipped-migrations.sh | jq -r '.hookSpecificOutput.permissionDecision // "allow"')
[[ "$got" == allow ]] || { echo "FAIL guard-shipped-migrations: new → $got"; FAIL=1; }

[[ $FAIL -eq 0 ]] && echo "OK — hook checks" || exit 1
