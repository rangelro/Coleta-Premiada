#!/bin/sh
set -eu

MONGO_HOST="${MONGO_HOST:-ms-db}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-${MONGO_INITDB_DATABASE:-coleta_db}}"
MONGO_AUTH_DB="${MONGO_AUTH_DB:-admin}"
MONGO_LOG_COLLECTION="${MONGO_LOG_COLLECTION:-audit_logs}"
MONGO_LOG_DATE_FIELD="${MONGO_LOG_DATE_FIELD:-created_at}"
RETENTION_DAYS="${LOG_RETENTION_DAYS:-90}"

log() {
    echo "[$(date -Iseconds)] $*"
}

if [ -n "${MONGO_USER:-}" ] && [ -n "${MONGO_PASSWORD:-}" ]; then
    AUTH_ARGS="--username ${MONGO_USER} --password ${MONGO_PASSWORD} --authenticationDatabase ${MONGO_AUTH_DB}"
else
    AUTH_ARGS=""
fi

log "Starting MongoDB log cleanup on ${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB}.${MONGO_LOG_COLLECTION}"

mongosh \
    "mongodb://${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB}" \
    $AUTH_ARGS \
    --quiet \
    --eval "
const retentionDays = Number('${RETENTION_DAYS}');
const cutoff = new Date(Date.now() - retentionDays * 24 * 60 * 60 * 1000);
const collectionName = '${MONGO_LOG_COLLECTION}';
const fieldName = '${MONGO_LOG_DATE_FIELD}';
const filter = {};
filter[fieldName] = { \$lt: cutoff };
const result = db.getCollection(collectionName).deleteMany(filter);
printjson({
  collection: collectionName,
  dateField: fieldName,
  cutoff,
  deletedCount: result.deletedCount
});
"

log "MongoDB log cleanup finished"
