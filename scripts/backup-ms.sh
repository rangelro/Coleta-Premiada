#!/bin/bash
# Dump diário do MongoDB (ms-db). Mantém 7 dias de histórico.
BACKUP_DIR=/backups
RETENTION_DAYS=7

while true; do
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    DUMP_DIR="$BACKUP_DIR/ms_${TIMESTAMP}"
    ARCHIVE="$BACKUP_DIR/ms_${TIMESTAMP}.tar.gz"

    mongodump \
        --host ms-db \
        --username "$MONGO_USER" \
        --password "$MONGO_PASSWORD" \
        --authenticationDatabase admin \
        --db "$MONGO_DB" \
        --out "$DUMP_DIR" 2>&1

    if [ -d "$DUMP_DIR" ]; then
        tar -czf "$ARCHIVE" -C "$BACKUP_DIR" "ms_${TIMESTAMP}" && rm -rf "$DUMP_DIR"
        find "$BACKUP_DIR" -name "ms_*.tar.gz" -mtime +"$RETENTION_DAYS" -delete
        echo "[$(date)] ms-db backup: $ARCHIVE"
    else
        echo "[$(date)] ms-db: banco ${MONGO_DB} ainda sem dados, backup ignorado"
    fi

    sleep 86400
done
