#!/bin/sh
set -eu

cat > /etc/crontabs/root <<EOF
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
PGPASSWORD=${PGPASSWORD}
PGHOST=${PGHOST:-core-db}
PGPORT=${PGPORT:-5432}
PGUSER=${PGUSER}
PGDATABASE=${PGDATABASE}
LOG_RETENTION_DAYS=${LOG_RETENTION_DAYS:-90}
LOG_CLEANUP_BATCH_SIZE=${LOG_CLEANUP_BATCH_SIZE:-5000}

15 2 * * * sh /maintenance/cleanup_logs.sh
45 2 * * * sh /maintenance/vacuum_analyze.sh
30 3 * * 0 sh /maintenance/reindex.sh
0  7 * * * python3 /maintenance/monitoring_report.py > /proc/1/fd/1 2>&1
EOF

echo "[$(date -Iseconds)] PostgreSQL maintenance cron configured"
exec crond -f -l 8
