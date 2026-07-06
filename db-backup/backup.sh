#!/bin/sh
# Executa um pg_dump do banco do Core e aplica a política de retenção:
#   - mantém os BACKUP_KEEP_DAILY backups diários mais recentes em daily/;
#   - no dia da semana BACKUP_WEEKLY_DAY (ISO: 1=segunda ... 7=domingo), também
#     copia o dump do dia para weekly/ e mantém os BACKUP_KEEP_WEEKLY mais recentes.
#
# Disparado pelo cron (ver entrypoint.sh) e pode ser executado manualmente para
# gerar um backup fora do horário agendado:
#   docker compose exec db-backup /scripts/backup.sh
set -eu

BASE_DIR="/backups/postgres"
DAILY_DIR="${BASE_DIR}/daily"
WEEKLY_DIR="${BASE_DIR}/weekly"

KEEP_DAILY="${BACKUP_KEEP_DAILY:-7}"
KEEP_WEEKLY="${BACKUP_KEEP_WEEKLY:-4}"
WEEKLY_DAY="${BACKUP_WEEKLY_DAY:-7}"

mkdir -p "$DAILY_DIR" "$WEEKLY_DIR"

TIMESTAMP="$(date +%Y-%m-%d_%H-%M-%S)"
FILENAME="coleta_premiada_${TIMESTAMP}.dump"
DAILY_PATH="${DAILY_DIR}/${FILENAME}"

export PGPASSWORD="${POSTGRES_PASSWORD}"

echo "[$(date -Iseconds)] Iniciando backup de '${POSTGRES_DB}' em ${POSTGRES_HOST}:${POSTGRES_PORT:-5432}..."

# Formato custom (-Fc): comprimido nativamente e restaurável com pg_restore
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

# Só renomeia para o nome final após o dump terminar, evitando que uma falha no
# meio do processo deixe um arquivo incompleto contabilizado na retenção.
mv "${DAILY_PATH}.tmp" "${DAILY_PATH}"
echo "[$(date -Iseconds)] Backup diário criado: ${DAILY_PATH}"

# Retenção diária: mantém apenas os KEEP_DAILY mais recentes.
ls -1t "${DAILY_DIR}"/*.dump 2>/dev/null | tail -n "+$((KEEP_DAILY + 1))" | xargs -r rm -f

# Backup semanal: no dia configurado, replica o dump do dia para weekly/.
DIA_SEMANA="$(date +%u)"
if [ "$DIA_SEMANA" = "$WEEKLY_DAY" ]; then
  WEEKLY_PATH="${WEEKLY_DIR}/${FILENAME}"
  cp "${DAILY_PATH}" "${WEEKLY_PATH}"
  echo "[$(date -Iseconds)] Backup semanal criado: ${WEEKLY_PATH}"

  ls -1t "${WEEKLY_DIR}"/*.dump 2>/dev/null | tail -n "+$((KEEP_WEEKLY + 1))" | xargs -r rm -f
fi

echo "[$(date -Iseconds)] Backup finalizado com sucesso."
