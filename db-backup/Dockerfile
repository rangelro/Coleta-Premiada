# Imagem do serviço de backup agendado do PostgreSQL.
# Usa a mesma base do banco (postgres:16-alpine) para garantir que pg_dump/pg_restore
# tenham sempre a mesma versão major do servidor, evitando incompatibilidades.
FROM postgres:16-alpine

WORKDIR /scripts

COPY entrypoint.sh backup.sh restore.sh ./
RUN chmod +x entrypoint.sh backup.sh restore.sh

ENTRYPOINT ["/scripts/entrypoint.sh"]
