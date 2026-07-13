#!/bin/sh
# Restaura o banco do Core a partir de um arquivo gerado por backup.sh.
#
# Uso:
#   docker compose exec db-backup /scripts/restore.sh <caminho_do_arquivo.dump>
#   docker compose exec db-backup /scripts/restore.sh -y                 (usa o mais recente sem confirmar)
#   docker compose exec db-backup /scripts/restore.sh                    (lista e pergunta qual usar)
#
# Exemplos:
#   docker compose exec db-backup /scripts/restore.sh coleta_premiada_2026-06-18_02-00-00.dump
#   docker compose exec db-backup /scripts/restore.sh /backups/postgres/daily/coleta_premiada_2026-06-18_02-00-00.dump
#
# ATENCAO: pg_restore --clean remove os objetos existentes antes de recria-los,
# ou seja, este processo SOBRESCREVE os dados atuais do banco de destino.
set -e

[ -f /scripts/env.sh ] && . /scripts/env.sh

BASE_DIR="${BACKUP_DIR:-/backups/postgres}"

# -y/--yes pula a confirmacao interativa (util para scripts/CI).
ASSUME_YES=""
if [ "$1" = "-y" ] || [ "$1" = "--yes" ]; then
  ASSUME_YES="1"
  shift
fi

# Aceita um caminho completo, so o nome do arquivo (resolve dentro do BASE_DIR
# procurando em daily/ e weekly/) ou nenhum argumento (usa o backup mais recente).
ARCHIVE="$1"
if [ -z "$ARCHIVE" ]; then
  ARCHIVE=$(find "$BASE_DIR" -type f -name '*.dump' 2>/dev/null | sort -r | head -n 1)
elif [ ! -f "$ARCHIVE" ]; then
  # Tenta como nome relativo dentro de daily/ ou weekly/
  if [ -f "${BASE_DIR}/daily/${ARCHIVE}" ]; then
    ARCHIVE="${BASE_DIR}/daily/${ARCHIVE}"
  elif [ -f "${BASE_DIR}/weekly/${ARCHIVE}" ]; then
    ARCHIVE="${BASE_DIR}/weekly/${ARCHIVE}"
  fi
fi

if [ -z "$ARCHIVE" ] || [ ! -f "$ARCHIVE" ]; then
  echo "Nenhum backup encontrado em ${BASE_DIR} (ou argumento invalido: '$1')." >&2
  exit 1
fi

echo "Backups disponiveis em ${BASE_DIR}:"
find "$BASE_DIR" -type f -name '*.dump' | sort
echo
echo "Restaurando a partir de: ${ARCHIVE}"
echo "ATENCAO: os dados atuais do banco '${POSTGRES_DB}' serao substituidos (--clean)."

if [ -z "$ASSUME_YES" ]; then
  printf 'Digite "sim" para confirmar a restauracao: '
  read -r CONFIRM
  if [ "$CONFIRM" != "sim" ]; then
    echo "Restauracao cancelada."
    exit 0
  fi
fi

export PGPASSWORD="${POSTGRES_PASSWORD}"

pg_restore \
  --host="${POSTGRES_HOST}" \
  --port="${POSTGRES_PORT:-5432}" \
  --username="${POSTGRES_USER}" \
  --dbname="${POSTGRES_DB}" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges \
  "$ARCHIVE"

echo "[$(date -Iseconds)] Restauracao concluida a partir de ${ARCHIVE}."
