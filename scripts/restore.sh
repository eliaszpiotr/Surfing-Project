#!/usr/bin/env bash
set -euo pipefail

if [ "${CONFIRM_RESTORE:-}" != "YES" ]; then
  echo "Refusing to restore without CONFIRM_RESTORE=YES."
  echo "Usage: CONFIRM_RESTORE=YES scripts/restore.sh backups/YYYYmmdd-HHMMSS"
  exit 1
fi

if [ "$#" -ne 1 ]; then
  echo "Usage: CONFIRM_RESTORE=YES scripts/restore.sh backups/YYYYmmdd-HHMMSS"
  exit 1
fi

COMPOSE="${COMPOSE:-docker compose}"
BACKUP_DIR="$1"
DATABASE_BACKUP="${BACKUP_DIR}/database.sql.gz"
MEDIA_BACKUP="${BACKUP_DIR}/media.tar.gz"

if [ ! -f "${DATABASE_BACKUP}" ]; then
  echo "Missing database backup: ${DATABASE_BACKUP}"
  exit 1
fi

if [ ! -f "${MEDIA_BACKUP}" ]; then
  echo "Missing media backup: ${MEDIA_BACKUP}"
  exit 1
fi

DB_NAME="$(${COMPOSE} exec -T db printenv POSTGRES_DB)"
DB_USER="$(${COMPOSE} exec -T db printenv POSTGRES_USER)"

echo "Restoring database ${DB_NAME}..."
${COMPOSE} exec -T db psql -U "${DB_USER}" "${DB_NAME}" -v ON_ERROR_STOP=1 -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
gunzip -c "${DATABASE_BACKUP}" | ${COMPOSE} exec -T db psql -U "${DB_USER}" "${DB_NAME}" -v ON_ERROR_STOP=1

echo "Restoring media..."
${COMPOSE} exec -T web sh -c "find /app/media -mindepth 1 -maxdepth 1 -exec rm -rf {} +"
${COMPOSE} exec -T web tar -C /app -xzf - < "${MEDIA_BACKUP}"

echo "Restore completed from ${BACKUP_DIR}"
