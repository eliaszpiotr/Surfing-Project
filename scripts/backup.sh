#!/usr/bin/env bash
set -euo pipefail

COMPOSE="${COMPOSE:-docker compose}"
BACKUP_ROOT="${BACKUP_ROOT:-backups}"
TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}"

DB_NAME="$(${COMPOSE} exec -T db printenv POSTGRES_DB)"
DB_USER="$(${COMPOSE} exec -T db printenv POSTGRES_USER)"

echo "Creating database backup..."
${COMPOSE} exec -T db pg_dump --no-owner --no-acl -U "${DB_USER}" "${DB_NAME}" | gzip -9 > "${BACKUP_DIR}/database.sql.gz"

echo "Creating media backup..."
${COMPOSE} exec -T web tar -C /app -czf - media > "${BACKUP_DIR}/media.tar.gz"

cat > "${BACKUP_DIR}/manifest.txt" <<MANIFEST
created_at_utc=${TIMESTAMP}
database=${DB_NAME}
database_file=database.sql.gz
media_file=media.tar.gz
MANIFEST

echo "Backup written to ${BACKUP_DIR}"
