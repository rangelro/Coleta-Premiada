#!/bin/sh
set -eu

TABLES="
audit_log
collection_registrocoleta
program_saldopontos
collection_contestacao
program_imovel
"

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
        -c "$1"
}

log "Starting REINDEX maintenance"

for table in $TABLES; do
    log "Running REINDEX TABLE CONCURRENTLY on ${table}"
    run_sql "REINDEX TABLE CONCURRENTLY ${table};"
done

log "REINDEX maintenance finished"
