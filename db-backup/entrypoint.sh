#!/bin/sh
# Ponto de entrada do container db-backup.
#
# Persiste as variaveis de ambiente para que o cron as enxergue,
# configura o cliente MinIO (se disponivel) e mantem o crond em execucao.
set -e

# O cron inicia os jobs com um ambiente "limpo", sem as variaveis do container.
# Persistimos o ambiente atual aqui para que backup.sh/restore.sh consigam
# acessar POSTGRES_HOST, POSTGRES_USER etc. quando disparados pelo cron.
printenv | sed "s/^\([A-Za-z_][A-Za-z0-9_]*\)=\(.*\)$/export \1='\2'/" > /scripts/env.sh
chmod +x /scripts/env.sh

mkdir -p "${BACKUP_DIR:-/backups/postgres}/daily" "${BACKUP_DIR:-/backups/postgres}/weekly"
touch /var/log/cron.log

# Configura o cliente MinIO se as variaveis estiverem presentes.
if [ -n "${MINIO_ENDPOINT:-}" ] && [ -n "${MINIO_ACCESS_KEY:-}" ]; then
  mc alias set minio "http://${MINIO_ENDPOINT}" "$MINIO_ACCESS_KEY" "$MINIO_SECRET_KEY" --quiet
  mc mb --ignore-existing "minio/${MINIO_BACKUP_BUCKET:-postgres-backups}" || true
  echo "MinIO configurado: http://${MINIO_ENDPOINT} (bucket: ${MINIO_BACKUP_BUCKET:-postgres-backups})"
fi

# Instalado via `crontab <file>` (crontab de usuario, sem campo de username) --
# nao usar /etc/cron.d/ aqui, pois esse diretorio e lido como crontab de
# sistema e exige um campo de usuario extra na linha.
echo "${CRON_SCHEDULE:-0 2 * * *} /scripts/backup.sh >> /var/log/cron.log 2>&1" > /scripts/crontab
crontab /scripts/crontab

cron

CRON_SCHEDULE="${CRON_SCHEDULE:-0 2 * * *}"
KEEP_DAILY="${BACKUP_KEEP_DAILY:-7}"
KEEP_WEEKLY="${BACKUP_KEEP_WEEKLY:-4}"

echo "[db-backup] Agendamento: '${CRON_SCHEDULE}'"
echo "[db-backup] Retencao: ${KEEP_DAILY} backups diarios + ${KEEP_WEEKLY} semanais"
echo "[db-backup] Destino: ${BACKUP_DIR:-/backups/postgres} (volume Docker)"

tail -f /var/log/cron.log
