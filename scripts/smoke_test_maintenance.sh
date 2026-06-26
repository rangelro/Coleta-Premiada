#!/usr/bin/env bash
# Smoke test das rotinas de manutencao do banco (MON-3).
# Uso:
#   bash scripts/smoke_test_maintenance.sh
#   RUN_MONGO_MAINTENANCE_TEST=1 bash scripts/smoke_test_maintenance.sh

set -uo pipefail

GREEN=$'\033[0;32m'
RED=$'\033[0;31m'
YELLOW=$'\033[1;33m'
NC=$'\033[0m'
PASS=0
FAIL=0
COMMAND_TIMEOUT="${COMMAND_TIMEOUT:-180}"
PGOPTIONS_SMOKE="${PGOPTIONS_SMOKE:--c lock_timeout=5s -c statement_timeout=120s}"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1090
  . <(sed 's/\r$//' .env)
  set +a
fi

PG_USER="${POSTGRES_USER:-coleta_user}"
PG_DB="${POSTGRES_DB:-coleta_premiada}"
TEST_TABLE="teste_manutencao_mon3"

dc() {
  docker compose -f docker-compose.yml "$@"
}

pass() { echo "${GREEN}PASS${NC} $1"; PASS=$((PASS + 1)); }
fail() { echo "${RED}FAIL${NC} $1"; FAIL=$((FAIL + 1)); }
skip() { echo "${YELLOW}SKIP${NC} $1"; }
info() { echo; echo "${YELLOW}== $1 ==${NC}"; }

run_check() {
  local desc="$1"
  shift
  local cmd=("$@")
  if [[ "${cmd[0]}" == "dc" ]]; then
    cmd=(docker compose -f docker-compose.yml "${cmd[@]:1}")
  fi
  if timeout "$COMMAND_TIMEOUT" "${cmd[@]}" >/tmp/mon3_smoke.out 2>/tmp/mon3_smoke.err; then
    pass "$desc"
    return 0
  fi
  fail "$desc"
  sed 's/^/  /' /tmp/mon3_smoke.err
  return 1
}

compose_services() {
  dc config --services 2>/dev/null
}

psql_maintenance() {
  dc run --rm -e PGOPTIONS="$PGOPTIONS_SMOKE" postgres-maintenance \
    psql -v ON_ERROR_STOP=1 -h core-db -U "$PG_USER" -d "$PG_DB" "$@"
}

psql_scalar() {
  psql_maintenance -At -c "$1" 2>/tmp/mon3_smoke.err | tr -d '[:space:]'
}

wait_for_core_db() {
  local attempt
  for attempt in $(seq 1 30); do
    if dc exec -T core-db pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}

info "1. Validacao estatica"
run_check "sintaxe dos scripts de maintenance" bash -n scripts/maintenance/*.sh
run_check "docker compose config valido" dc config --quiet

services="$(compose_services)"
if grep -qx "postgres-maintenance" <<<"$services"; then
  pass "servico postgres-maintenance definido"
else
  fail "servico postgres-maintenance definido"
fi

if grep -qx "mongo-maintenance" <<<"$services"; then
  pass "servico mongo-maintenance definido"
else
  fail "servico mongo-maintenance definido"
fi

info "2. PostgreSQL disponivel"
if dc up -d core-db >/tmp/mon3_smoke.out 2>/tmp/mon3_smoke.err; then
  pass "core-db iniciado"
else
  fail "core-db iniciado"
  sed 's/^/  /' /tmp/mon3_smoke.err
fi

if wait_for_core_db; then
  pass "core-db saudavel"
else
  fail "core-db saudavel"
fi

run_check "conexao via postgres-maintenance" \
  dc run --rm -e PGOPTIONS="$PGOPTIONS_SMOKE" postgres-maintenance \
  psql -h core-db -U "$PG_USER" -d "$PG_DB" -c "SELECT 1;"

info "3. Cleanup de audit_log"
HAS_AUDIT_LOG=0
if [[ "$(psql_scalar "SELECT to_regclass('public.audit_log') IS NOT NULL;")" == "t" ]]; then
  HAS_AUDIT_LOG=1
  pass "tabela audit_log existe"
else
  fail "tabela audit_log existe; rode as migrations antes do smoke test"
fi

if [[ "$HAS_AUDIT_LOG" == "1" ]]; then
  psql_maintenance -c "DELETE FROM audit_log WHERE tabela = '${TEST_TABLE}';" >/dev/null 2>/tmp/mon3_smoke.err

  if psql_maintenance -c "INSERT INTO audit_log (timestamp, operacao, tabela) VALUES (NOW() - INTERVAL '91 days', 'SELECT', '${TEST_TABLE}');" >/tmp/mon3_smoke.out 2>/tmp/mon3_smoke.err; then
    pass "registro temporario antigo inserido"
  else
    fail "registro temporario antigo inserido"
    sed 's/^/  /' /tmp/mon3_smoke.err
  fi

  before_count="$(psql_scalar "SELECT COUNT(*) FROM audit_log WHERE tabela = '${TEST_TABLE}';")"
  if [[ "$before_count" == "1" ]]; then
    pass "registro temporario encontrado antes do cleanup"
  else
    fail "registro temporario encontrado antes do cleanup"
  fi

  run_check "cleanup_logs.sh executa" \
    dc run --rm -e PGOPTIONS="$PGOPTIONS_SMOKE" postgres-maintenance sh /maintenance/cleanup_logs.sh

  after_count="$(psql_scalar "SELECT COUNT(*) FROM audit_log WHERE tabela = '${TEST_TABLE}';")"
  if [[ "$after_count" == "0" ]]; then
    pass "cleanup_logs.sh removeu registro antigo"
  else
    fail "cleanup_logs.sh removeu registro antigo"
  fi
else
  skip "cleanup_logs.sh nao executado porque audit_log nao existe"
fi

info "4. Vacuum e reindex"
if [[ "$HAS_AUDIT_LOG" == "1" ]]; then
  run_check "vacuum_analyze.sh executa" \
    dc run --rm -e PGOPTIONS="$PGOPTIONS_SMOKE" postgres-maintenance sh /maintenance/vacuum_analyze.sh
  run_check "reindex.sh executa" \
    dc run --rm -e PGOPTIONS="$PGOPTIONS_SMOKE" postgres-maintenance sh /maintenance/reindex.sh
else
  skip "vacuum_analyze.sh e reindex.sh nao executados porque as tabelas do core nao existem"
fi

info "5. Cron do postgres-maintenance"
if dc up -d postgres-maintenance >/tmp/mon3_smoke.out 2>/tmp/mon3_smoke.err; then
  pass "postgres-maintenance iniciou"
else
  fail "postgres-maintenance iniciou"
  sed 's/^/  /' /tmp/mon3_smoke.err
fi

sleep 2
if dc logs --tail=30 postgres-maintenance 2>/dev/null | grep -q "PostgreSQL maintenance cron configured"; then
  pass "cron do postgres-maintenance configurado"
else
  fail "cron do postgres-maintenance configurado"
fi

info "6. MongoDB opcional"
if [[ "${RUN_MONGO_MAINTENANCE_TEST:-0}" == "1" ]]; then
  run_check "cleanup_mongo_logs.sh executa" \
    dc run --rm mongo-maintenance sh /maintenance/cleanup_mongo_logs.sh
else
  skip "cleanup Mongo nao executado; use RUN_MONGO_MAINTENANCE_TEST=1 para habilitar"
fi

rm -f /tmp/mon3_smoke.out /tmp/mon3_smoke.err

echo
echo "Resultado: ${GREEN}${PASS} PASS${NC} / ${RED}${FAIL} FAIL${NC}"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
