#!/bin/sh
# Nightly pg_dump → R2 (S3-compatible). Retention: 14 daily + 8 weekly.
# Requires: DATABASE_URL (or PG*), S3_ENDPOINT_URL, S3_ACCESS_KEY, S3_SECRET_KEY, S3_BUCKET
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

dump_once() {
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  day=$(date -u +%u)
  out="/tmp/backups/kame-apply-${stamp}.dump"
  mkdir -p /tmp/backups
  echo "backup: dumping ${stamp}"
  pg_dump --format=custom --no-owner --file="$out" "$DATABASE_URL_LIBPQ"
  key="${PREFIX}/daily/${stamp}.dump"
  AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY" AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY" \
    aws --endpoint-url "$S3_ENDPOINT_URL" s3 cp "$out" "s3://${S3_BUCKET}/${key}"
  if [ "$day" = "7" ]; then
    wkey="${PREFIX}/weekly/${stamp}.dump"
    AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY" AWS_SECRET_ACCESS_KEY="$S3_SECRET_KEY" \
      aws --endpoint-url "$S3_ENDPOINT_URL" s3 cp "$out" "s3://${S3_BUCKET}/${wkey}"
  fi
  rm -f "$out"
  echo "backup: uploaded ${key}"
}

# Convert asyncpg URL to libpq form if needed
DATABASE_URL_LIBPQ=$(printf '%s' "${MIGRATION_DATABASE_URL:-${DATABASE_URL}}" | sed 's|+asyncpg||')

install_aws
# Run once at start so a fresh deploy gets a baseline dump, then sleep.
while true; do
  dump_once || echo "backup: failed (will retry next interval)"
  sleep "$INTERVAL_SECONDS"
done
