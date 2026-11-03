#!/bin/sh
# Nightly pg_dump → R2 (S3-compatible). Retention: 14 daily + 8 weekly.
# Requires: MIGRATION_DATABASE_URL (owner role: the app role is RLS-restricted and dumps empty),
#           S3_ENDPOINT_URL, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET
set -eu

INTERVAL_SECONDS="${BACKUP_INTERVAL_SECONDS:-86400}"
PREFIX="${BACKUP_PREFIX:-backups/postgres}"
KEEP_DAILY="${BACKUP_KEEP_DAILY:-14}"
KEEP_WEEKLY="${BACKUP_KEEP_WEEKLY:-8}"

install_aws() {
  if command -v aws >/dev/null 2>&1; then
    return 0
  fi
  apk add --no-cache aws-cli >/dev/null 2>&1 || true
}

s3() {
  AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY" AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY" \
    aws --endpoint-url "$S3_ENDPOINT_URL" "$@"
}

require_owner_url() {
  if [ -z "${MIGRATION_DATABASE_URL:-}" ]; then
    echo "backup: MIGRATION_DATABASE_URL (owner role) is required; the app role cannot read tenant rows" >&2
    exit 1
  fi
}

prune() {
  # Keep the newest $2 objects under $1, delete the rest.
  dir="$1"
  keep="$2"
  s3 s3 ls "s3://${S3_BUCKET}/${dir}/" | awk '{print $4}' | sort -r | tail -n +"$((keep + 1))" |
    while read -r name; do
      [ -n "$name" ] || continue
      s3 s3 rm "s3://${S3_BUCKET}/${dir}/${name}" >/dev/null
      echo "backup: pruned ${dir}/${name}"
    done
}

dump_once() {
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  day=$(date -u +%u)
  out="/tmp/backups/kame-apply-${stamp}.dump"
  mkdir -p /tmp/backups
  echo "backup: dumping ${stamp}"
  pg_dump --format=custom --no-owner --file="$out" "$DATABASE_URL_LIBPQ"
  if [ ! -s "$out" ]; then
    echo "backup: dump is empty — aborting" >&2
    return 1
  fi
  # A dump that cannot be listed is not a backup.
  pg_restore --list "$out" >/dev/null
  key="${PREFIX}/daily/${stamp}.dump"
  s3 s3 cp "$out" "s3://${S3_BUCKET}/${key}"
  if [ "$day" = "7" ]; then
    wkey="${PREFIX}/weekly/${stamp}.dump"
    s3 s3 cp "$out" "s3://${S3_BUCKET}/${wkey}"
  fi
  rm -f "$out"
  echo "backup: uploaded ${key}"
  prune "${PREFIX}/daily" "$KEEP_DAILY"
  prune "${PREFIX}/weekly" "$KEEP_WEEKLY"
}

require_owner_url
# Convert asyncpg URL to libpq form if needed
DATABASE_URL_LIBPQ=$(printf '%s' "${MIGRATION_DATABASE_URL}" | sed 's|+asyncpg||')

install_aws
failures=0
# Run once at start so a fresh deploy gets a baseline dump, then sleep.
while true; do
  if dump_once; then
    failures=0
  else
    failures=$((failures + 1))
    echo "backup: failed (${failures} in a row); retrying next interval" >&2
    if [ "$failures" -ge 3 ]; then
      echo "backup: three consecutive failures — exiting so the supervisor alerts" >&2
      exit 1
    fi
  fi
  sleep "$INTERVAL_SECONDS"
done
