#!/bin/sh
set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="/backups/core_${TIMESTAMP}.sql.gz"

pg_dump -h "$PGHOST" -U "$PGUSER" "$PGDATABASE" | gzip > "$BACKUP_FILE"

# Keep only the 7 most recent backups
find /backups -name 'core_*.sql.gz' -type f | sort | head -n -7 | xargs -r rm -f

echo "Backup saved: $BACKUP_FILE"

sleep 86400
