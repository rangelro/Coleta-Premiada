#!/bin/sh
# Ponto de entrada do container db-backup.
#
# Monta o crontab a partir de BACKUP_CRON_SCHEDULE e mantém o crond do busybox
# (já incluso na imagem base postgres:16-alpine) em foreground como PID 1.
set -eu

CRON_SCHEDULE="${BACKUP_CRON_SCHEDULE:-0 2 * * *}"

mkdir -p /backups/postgres/daily /backups/postgres/weekly

# Redireciona a saída do job para o stdout/stderr do PID 1 (visível em `docker compose logs db-backup`).
echo "${CRON_SCHEDULE} /scripts/backup.sh >> /proc/1/fd/1 2>> /proc/1/fd/2" > /etc/crontabs/root

echo "[db-backup] Agendamento: '${CRON_SCHEDULE}'"
echo "[db-backup] Retenção: ${BACKUP_KEEP_DAILY:-7} backups diários + ${BACKUP_KEEP_WEEKLY:-4} semanais"
echo "[db-backup] Destino: /backups/postgres (volume Docker)"

exec crond -f -d 8
