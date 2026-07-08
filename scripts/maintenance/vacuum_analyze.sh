#!/bin/sh
set -eu

TABLES="
accounts_usuario
accounts_role
accounts_usuario_roles
program_programa
program_regraprograma
program_imovel
program_imovel_moradores
program_saldopontos
program_consolidacao
program_constantepontuacao
collection_registrocoleta
collection_evidencia
collection_contestacao
reports_relatoriollm
audit_log
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

log "Starting VACUUM ANALYZE maintenance"

for table in $TABLES; do
    log "Running VACUUM ANALYZE on ${table}"
    run_sql "VACUUM ANALYZE ${table};"
done

log "VACUUM ANALYZE maintenance finished"
