# Imagem do serviço de backup agendado do PostgreSQL.
# Usa a mesma base do banco (postgres:16-alpine) para garantir que pg_dump/pg_restore
# tenham sempre a mesma versão major do servidor, evitando incompatibilidades.
FROM postgres:16-alpine

# mc: cliente MinIO para upload offsite dos backups.
# Atualize MC_VERSION consultando https://github.com/minio/mc/releases
ARG MC_VERSION=RELEASE.2025-08-13T08-35-41Z

RUN apk add --no-cache curl \
    && ARCH=$(uname -m) \
    && curl -fsSL \
         "https://dl.min.io/client/mc/release/linux-${ARCH}/archive/mc.${MC_VERSION}" \
         -o /usr/local/bin/mc \
    && chmod +x /usr/local/bin/mc

WORKDIR /scripts

COPY entrypoint.sh backup.sh restore.sh ./
RUN chmod +x entrypoint.sh backup.sh restore.sh

ENTRYPOINT ["/scripts/entrypoint.sh"]
