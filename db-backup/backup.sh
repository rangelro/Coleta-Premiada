#!/bin/sh
# Executa um pg_dump do banco do Core e aplica a politica de retencao:
#   - mantem os BACKUP_KEEP_DAILY backups diarios mais recentes em daily/;
#   - no dia da semana BACKUP_WEEKLY_DAY (ISO: 1=segunda ... 7=domingo), tambem
#     copia o dump do dia para weekly/ e mantem os BACKUP_KEEP_WEEKLY mais recentes.
#
# Disparado pelo cron (ver entrypoint.sh) e pode ser executado manualmente para
# gerar um backup fora do horario agendado:
#   docker compose exec db-backup /scripts/backup.sh
set -eu

[ -f /scripts/env.sh ] && . /scripts/env.sh

BASE_DIR="${BACKUP_DIR:-/backups/postgres}"
DAILY_DIR="${BASE_DIR}/daily"
WEEKLY_DIR="${BASE_DIR}/weekly"

KEEP_DAILY="${BACKUP_KEEP_DAILY:-7}"
KEEP_WEEKLY="${BACKUP_KEEP_WEEKLY:-4}"
WEEKLY_DAY="${BACKUP_WEEKLY_DAY:-7}"

# Envia notificacao via webhook (Slack, Discord, ntfy.sh, etc.).
# Nao interrompe o script se o curl falhar.
notify() {
  LEVEL="$1"
  MSG="$2"
  echo "[${LEVEL}] $MSG"
  if [ -n "${NOTIFY_WEBHOOK_URL:-}" ]; then
    curl -sf -X POST "$NOTIFY_WEBHOOK_URL" \
      -H 'Content-Type: application/json' \
      -d "{\"text\":\"[${LEVEL}] ${MSG}\"}" || true
  fi
}

# Flag de sucesso: se o script sair com EXIT=0 antes de ser setada, houve falha.
BACKUP_OK=0
on_exit() {
  if [ "$BACKUP_OK" -eq 0 ]; then
    notify "ERRO" "Backup de '${POSTGRES_DB}' falhou em $(date -Iseconds). Verifique os logs do container db-backup."
  fi
}
trap on_exit EXIT

mkdir -p "$DAILY_DIR" "$WEEKLY_DIR"

TIMESTAMP="$(date +%Y-%m-%d_%H-%M-%S)"
FILENAME="coleta_premiada_${TIMESTAMP}.dump"
DAILY_PATH="${DAILY_DIR}/${FILENAME}"

export PGPASSWORD="${POSTGRES_PASSWORD}"

echo "[$(date -Iseconds)] Iniciando backup de '${POSTGRES_DB}' em ${POSTGRES_HOST}:${POSTGRES_PORT:-5432}..."

# Formato custom (-Fc): comprimido nativamente e restauravel com pg_restore
# (suporta restore seletivo e paralelo, diferente de um dump em texto puro).
pg_dump \
  --host="${POSTGRES_HOST}" \
  --port="${POSTGRES_PORT:-5432}" \
  --username="${POSTGRES_USER}" \
  --format=custom \
  --no-owner \
  --no-privileges \
  --file="${DAILY_PATH}.tmp" \
  "${POSTGRES_DB}"

# So renomeia para o nome final apos o dump terminar, evitando que uma falha no
# meio do processo deixe um arquivo incompleto contabilizado na retencao.
mv "${DAILY_PATH}.tmp" "${DAILY_PATH}"
echo "[$(date -Iseconds)] Backup diario criado: ${DAILY_PATH}"

# Verifica integridade do arquivo de dump (formato custom do PostgreSQL).
pg_restore --list "${DAILY_PATH}" > /dev/null
echo "[$(date -Iseconds)] Integridade verificada: ${DAILY_PATH}"

# Upload offsite para MinIO (opcional -- requer MINIO_ENDPOINT configurado).
if [ -n "${MINIO_ENDPOINT:-}" ]; then
  mc cp "${DAILY_PATH}" "minio/${MINIO_BACKUP_BUCKET:-postgres-backups}/"
  echo "[$(date -Iseconds)] Upload MinIO concluido: ${MINIO_BACKUP_BUCKET:-postgres-backups}/$(basename "${DAILY_PATH}")"
fi

# Retencao diaria: mantem apenas os KEEP_DAILY mais recentes.
ls -1t "${DAILY_DIR}"/*.dump 2>/dev/null | tail -n "+$((KEEP_DAILY + 1))" | xargs -r rm -f

# Backup semanal: no dia configurado, replica o dump do dia para weekly/.
DIA_SEMANA="$(date +%u)"
if [ "$DIA_SEMANA" = "$WEEKLY_DAY" ]; then
  WEEKLY_PATH="${WEEKLY_DIR}/${FILENAME}"
  cp "${DAILY_PATH}" "${WEEKLY_PATH}"
  echo "[$(date -Iseconds)] Backup semanal criado: ${WEEKLY_PATH}"

  ls -1t "${WEEKLY_DIR}"/*.dump 2>/dev/null | tail -n "+$((KEEP_WEEKLY + 1))" | xargs -r rm -f
fi

BACKUP_OK=1
notify "OK" "Backup de '${POSTGRES_DB}' concluido: ${FILENAME}"
echo "[$(date -Iseconds)] Backup finalizado com sucesso."
