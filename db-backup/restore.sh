#!/bin/sh
# Restaura o banco do Core a partir de um arquivo gerado por backup.sh.
#
# Uso:
#   docker compose exec db-backup /scripts/restore.sh <caminho_do_arquivo.dump>
#
# Exemplos:
#   docker compose exec db-backup /scripts/restore.sh /backups/postgres/daily/coleta_premiada_2026-06-18_02-00-00.dump
#   docker compose exec db-backup /scripts/restore.sh /backups/postgres/weekly/coleta_premiada_2026-06-14_02-00-00.dump
#
# Sem argumentos, lista os backups disponíveis no volume.
#
# ATENÇÃO: pg_restore --clean remove os objetos existentes antes de recriá-los,
# ou seja, este processo SOBRESCREVE os dados atuais do banco de destino.
set -eu

ARQUIVO="${1:-}"

if [ -z "$ARQUIVO" ]; then
  echo "Uso: $0 <caminho_do_arquivo_de_backup>"
  echo
  echo "Backups disponíveis em ${BASE_DIR:-/backups/postgres}:"
  find /backups/postgres -type f -name '*.dump' | sort
  exit 1
fi

if [ ! -f "$ARQUIVO" ]; then
  echo "Arquivo não encontrado: ${ARQUIVO}"
  exit 1
fi

export PGPASSWORD="${POSTGRES_PASSWORD}"

echo "Banco de destino : ${POSTGRES_DB} (${POSTGRES_HOST}:${POSTGRES_PORT:-5432})"
echo "Arquivo de origem: ${ARQUIVO}"
echo "Esta operação substitui todos os dados atuais do banco de destino."
printf 'Digite "sim" para confirmar a restauração: '
read -r CONFIRMACAO

if [ "$CONFIRMACAO" != "sim" ]; then
  echo "Operação cancelada."
  exit 1
fi

pg_restore \
  --host="${POSTGRES_HOST}" \
  --port="${POSTGRES_PORT:-5432}" \
  --username="${POSTGRES_USER}" \
  --dbname="${POSTGRES_DB}" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  "$ARQUIVO"

echo "[$(date -Iseconds)] Restauração concluída a partir de ${ARQUIVO}."
