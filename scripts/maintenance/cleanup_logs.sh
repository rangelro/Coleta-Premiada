#!/bin/sh
set -eu

RETENTION_DAYS="${LOG_RETENTION_DAYS:-90}"
BATCH_SIZE="${LOG_CLEANUP_BATCH_SIZE:-5000}"

log() {
    echo "[$(date -Iseconds)] $*"
}

run_sql() {
    psql \
        -v ON_ERROR_STOP=1 \
        -h "${PGHOST:-core-db}" \
        -p "${PGPORT:-5432}" \
        -U "${PGUSER:?PGUSER is required}" \
        -d "${PGDATABASE:?PGDATABASE is required}" \
        -At \
        -c "$1"
}

log "Starting audit_log cleanup older than ${RETENTION_DAYS} days"

while :; do
    deleted_count="$(
        run_sql "
WITH deleted AS (
    DELETE FROM audit_log
    WHERE id IN (
        SELECT id
        FROM audit_log
        WHERE timestamp < NOW() - INTERVAL '${RETENTION_DAYS} days'
        ORDER BY timestamp
        LIMIT ${BATCH_SIZE}
    )
    RETURNING 1
)
SELECT COUNT(*) FROM deleted;
"
    )"

    log "Deleted ${deleted_count} audit_log rows"

    if [ "$deleted_count" -eq 0 ]; then
        break
    fi
done

log "Refreshing audit_log statistics"
psql \
    -v ON_ERROR_STOP=1 \
    -h "${PGHOST:-core-db}" \
    -p "${PGPORT:-5432}" \
    -U "${PGUSER:?PGUSER is required}" \
    -d "${PGDATABASE:?PGDATABASE is required}" \
    -c "VACUUM ANALYZE audit_log;"

log "audit_log cleanup finished"
