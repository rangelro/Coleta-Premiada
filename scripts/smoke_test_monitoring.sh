#!/usr/bin/env bash
# Smoke test da stack de monitoramento (MON-2).
# Verifica pg_stat_statements, plugin Prometheus do RabbitMQ, django-prometheus,
# queries customizadas, targets/alertas Prometheus e provisioning do Grafana.
# Uso: bash scripts/smoke_test_monitoring.sh   (a partir da raiz do repo)

set -uo pipefail

GREEN=$'\033[0;32m'; RED=$'\033[0;31m'; YELLOW=$'\033[1;33m'; NC=$'\033[0m'
PASS=0; FAIL=0

# Carrega .env (credenciais do Postgres) se existir.
# Usa process substitution + sed para tolerar arquivos com CRLF (Windows).
if [[ -f .env ]]; then set -a; . <(sed 's/\r$//' .env); set +a; fi
PG_USER="${POSTGRES_USER:-coleta_user}"
PG_DB="${POSTGRES_DB:-coleta_premiada}"
GF_USER="${GF_ADMIN_USER:-admin}"
GF_PASS="${GF_ADMIN_PASS:-senha_admin_grafana}"

pass() { echo "${GREEN}✓ PASS${NC} $1"; PASS=$((PASS+1)); }
fail() { echo "${RED}✗ FAIL${NC} $1"; FAIL=$((FAIL+1)); }
info() { echo; echo "${YELLOW}== $1 ==${NC}"; }

# check_grep <desc> <padrão> <comando...>
# Captura a saída em variável e faz grep via here-string. Evita que, sob
# 'pipefail', um 'curl | grep -q' retorne erro 23 (write error) quando o
# grep fecha o pipe cedo em respostas grandes (ex.: /metrics do RabbitMQ).
check_grep() {
  local desc="$1" pattern="$2"; shift 2
  local out; out="$("$@" 2>/dev/null)"
  if grep -qE -- "$pattern" <<<"$out"; then pass "$desc"; else fail "$desc"; fi
}

info "1. Containers em execução"
running=$(docker compose ps --status running --services 2>/dev/null)
for s in postgres rabbitmq core; do
  echo "$running" | grep -qx "$s" && pass "serviço $s" || fail "serviço $s (rode 'make up')"
done
mrunning=$(docker compose -f docker-compose.monitoring.yml ps --status running --services 2>/dev/null)
for s in prometheus grafana postgres_exporter node_exporter; do
  echo "$mrunning" | grep -qx "$s" && pass "serviço $s" || fail "serviço $s (rode 'make monitoring-up')"
done

info "2. pg_stat_statements"
ext=$(docker compose exec -T postgres psql -U "$PG_USER" -d "$PG_DB" -tAc \
  "SELECT 1 FROM pg_extension WHERE extname='pg_stat_statements';" 2>/dev/null | tr -d '[:space:]')
[[ "$ext" == "1" ]] && pass "extensão pg_stat_statements ativa" \
  || fail "extensão ausente (CREATE EXTENSION pg_stat_statements;)"

info "3. RabbitMQ (porta 15692)"
check_grep "métricas rabbitmq_* expostas" "rabbitmq_" curl -s http://localhost:15692/metrics

info "4. django-prometheus (porta 8001)"
django_metrics="$(curl -s http://localhost:8001/metrics 2>/dev/null)"
grep -qE "# HELP" <<<"$django_metrics" && pass "/metrics responde formato Prometheus" \
  || fail "/metrics responde formato Prometheus"
if grep -q "django_http_requests_total" <<<"$django_metrics"; then
  pass "métrica django_http_requests_total presente"
else
  echo "${YELLOW}› NOTA${NC} django_http_* aparece após o primeiro request à API"
fi

info "5. postgres_exporter custom queries (porta 9187)"
check_grep "métrica pg_coletas_recentes" "pg_coletas_recentes" curl -s http://localhost:9187/metrics
check_grep "métrica pg_long_running_queries" "pg_long_running_queries" curl -s http://localhost:9187/metrics

info "6. Prometheus targets (porta 9090)"
targets=$(curl -s http://localhost:9090/api/v1/targets 2>/dev/null)
if echo "$targets" | grep -q '"health":"down"'; then
  fail "há targets em estado DOWN"
elif echo "$targets" | grep -q '"health":"up"'; then
  pass "nenhum target DOWN"
else
  fail "Prometheus não retornou targets"
fi
for job in prometheus postgres node rabbitmq django-core; do
  echo "$targets" | grep -q "\"job\":\"$job\"" && pass "job '$job' presente" || fail "job '$job' ausente"
done

info "7. Regras de alerta Prometheus"
rules=$(curl -s http://localhost:9090/api/v1/rules 2>/dev/null)
for r in PGConnectionsHigh PGSlowQuery DiskSpaceHigh RabbitMQQueueHigh; do
  echo "$rules" | grep -q "$r" && pass "alerta $r carregado" || fail "alerta $r ausente"
done

info "8. Grafana (porta 3000)"
gf_health="$(curl -s -u "$GF_USER:$GF_PASS" http://localhost:3000/api/health 2>/dev/null)"
grep -qE '"database": *"ok"' <<<"$gf_health" && pass "Grafana health OK" || fail "Grafana health"
gf_ds="$(curl -s -u "$GF_USER:$GF_PASS" http://localhost:3000/api/datasources 2>/dev/null)"
grep -qi 'prometheus' <<<"$gf_ds" && pass "datasource Prometheus provisionado" || fail "datasource ausente"
gf_dash="$(curl -s -u "$GF_USER:$GF_PASS" "http://localhost:3000/api/search?query=Coleta" 2>/dev/null)"
grep -qE 'coleta-premiada-main|Coleta Premiada' <<<"$gf_dash" && pass "dashboard provisionado" || fail "dashboard ausente"

echo
echo "──────────────────────────────────────────"
echo "Resultado: ${GREEN}${PASS} PASS${NC} / ${RED}${FAIL} FAIL${NC}"
[[ $FAIL -eq 0 ]] && exit 0 || exit 1
