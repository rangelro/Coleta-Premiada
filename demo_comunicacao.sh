#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  DEMO — Coleta Premiada: Fluxo Completo de Comunicação
# ═══════════════════════════════════════════════════════════════════
#
#  Como rodar:
#    1. Certifique-se de que o Docker está rodando
#    2. Na raiz do projeto, execute:
#
#       bash demo_comunicacao.sh
#
#  Pré-requisitos:
#    - Docker e Docker Compose instalados
#    - Containers do projeto configurados (docker compose up -d)
#    - Portas 8000, 8001, 5432, 27017, 5672 livres
#
# ═══════════════════════════════════════════════════════════════════
#
#  Este script demonstra a comunicação entre os componentes:
#
#  [Coletor] → POST → [Microserviço Django] → MongoDB
#                            ↓
#                       [RabbitMQ] (fila pesagens)
#                            ↓
#                    [Core Consumer] → PostgreSQL
#
# ═══════════════════════════════════════════════════════════════════

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

separator() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

header() {
    echo -e "${BOLD}${CYAN}$1${NC}"
}

step() {
    echo -e "  ${YELLOW}▶${NC} $1"
}

success() {
    echo -e "  ${GREEN}✅ $1${NC}"
}

info() {
    echo -e "  ${MAGENTA}📌 $1${NC}"
}

# ─── Verificação dos containers ────────────────────────────────────
echo ""
echo ""
echo -e "${BOLD}${CYAN}"
echo "  ╔═══════════════════════════════════════════════════════╗"
echo "  ║        COLETA PREMIADA — Demo de Comunicação         ║"
echo "  ╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

separator
header "ETAPA 0 — Verificando containers Docker"
echo ""

CONTAINERS=("postgres" "mongodb" "rabbitmq" "collection-microservice" "core" "core-consumer")
ALL_UP=true

for c in "${CONTAINERS[@]}"; do
    STATUS=$(docker compose ps --format '{{.State}}' "$c" 2>/dev/null || echo "not found")
    if [[ "$STATUS" == "running" ]]; then
        echo -e "  ${GREEN}●${NC} $c: ${GREEN}running${NC}"
    else
        echo -e "  ${RED}●${NC} $c: ${RED}$STATUS${NC}"
        ALL_UP=false
    fi
done

if [ "$ALL_UP" = false ]; then
    echo ""
    step "Subindo containers que estão parados..."
    docker compose up -d
    sleep 5
fi

# ─── ETAPA 1: Estado inicial dos bancos ────────────────────────────
separator
header "ETAPA 1 — Estado inicial dos bancos de dados"
echo ""

step "Consultando MongoDB (Microserviço de Coleta)..."
echo ""
MONGO_COUNT=$(docker compose exec -T mongodb mongosh \
    --username mongo_user --password mongo_senha_local --authenticationDatabase admin \
    coleta_db --quiet --eval "db.api_pesagem.countDocuments()" 2>/dev/null || echo "erro")
echo -e "  ${CYAN}MongoDB${NC} → api_pesagem: ${BOLD}${MONGO_COUNT} documentos${NC}"

echo ""
step "Consultando PostgreSQL (Core)..."
echo ""
PG_COLETAS=$(docker compose exec -T core python manage.py shell -c "
from collection.models import RegistroColeta
print(RegistroColeta.objects.count())
" 2>/dev/null | tail -1)
PG_SALDOS=$(docker compose exec -T core python manage.py shell -c "
from program.models import SaldoPontos
for s in SaldoPontos.objects.all():
    print(f'  {s.imovel.inscricao} | Desconto: {s.desconto_percentual}% | {s.total_kg}kg')
if not SaldoPontos.objects.exists():
    print('  (nenhum saldo registrado)')
" 2>/dev/null | grep -v "objects imported")
echo -e "  ${CYAN}PostgreSQL${NC} → RegistroColeta: ${BOLD}${PG_COLETAS} registros${NC}"
echo -e "  ${CYAN}PostgreSQL${NC} → SaldoPontos:"
echo -e "${PG_SALDOS}"

echo ""
step "Consultando RabbitMQ (Fila de Mensagens)..."
echo ""
RABBIT_INFO=$(docker compose exec -T rabbitmq rabbitmqctil list_queues name messages consumers 2>/dev/null | grep pesagens || echo "pesagens 0 0")
echo -e "  ${CYAN}RabbitMQ${NC} → Fila: ${BOLD}${RABBIT_INFO}${NC}"

# ─── ETAPA 2: Simular coletas ─────────────────────────────────────
separator
header "ETAPA 2 — Simulando 3 coletas via Microserviço (POST → MongoDB → RabbitMQ)"
echo ""

declare -a MATERIAIS=("papel" "plastico" "metal")
declare -a PESOS=("5.000" "8.500" "12.000")
declare -a DESCRICOES=("Papel/Papelão" "Plástico" "Metal")
declare -a IDS=()

for i in 0 1 2; do
    MAT=${MATERIAIS[$i]}
    PESO=${PESOS[$i]}
    DESC=${DESCRICOES[$i]}

    step "Coleta $((i+1))/3: ${PESO}kg de ${DESC}..."

    RESPONSE=$(curl -s -X POST http://localhost:8001/api/pesagens/ \
        -H "Content-Type: application/json" \
        -d "{
            \"inscricao_imobiliaria\": \"0001.001.0001\",
            \"material\": \"${MAT}\",
            \"peso_kg\": \"${PESO}\",
            \"agente_id\": \"agente-demo\"
        }")

    ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null)
    STATUS=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null)
    IDS+=("$ID")

    echo -e "    Resposta: ${GREEN}id=${ID}, status=${STATUS}${NC}"
    echo ""
done

success "3 coletas enviadas ao Microserviço!"

# ─── ETAPA 3: Verificar MongoDB ───────────────────────────────────
separator
header "ETAPA 3 — Verificando persistência no MongoDB"
echo ""

step "Buscando os documentos recém-criados..."
echo ""

docker compose exec -T mongodb mongosh \
    --username mongo_user --password mongo_senha_local --authenticationDatabase admin \
    coleta_db --quiet --eval "
    const docs = db.api_pesagem.find().sort({data_hora: -1}).limit(3).toArray();
    docs.reverse().forEach((d, i) => {
        print('  Documento ' + (i+1) + ':');
        print('    _id:       ' + d._id);
        print('    material:  ' + d.material);
        print('    peso_kg:   ' + d.peso_kg);
        print('    status:    ' + d.status);
        print('    data_hora: ' + d.data_hora);
        print('');
    });
" 2>/dev/null

success "Dados persistidos no MongoDB com status 'publicado'!"
info "O microserviço salva no MongoDB E publica na fila RabbitMQ simultaneamente."

# ─── ETAPA 4: Aguardar processamento pelo Consumer ────────────────
separator
header "ETAPA 4 — Aguardando Core Consumer processar da fila RabbitMQ..."
echo ""

step "O consumer lê da fila 'pesagens' e salva no PostgreSQL..."
echo ""

# Aguardar o consumer processar (máx 15 segundos)
for attempt in $(seq 1 15); do
    PROCESSED=$(docker compose exec -T core python manage.py shell -c "
from collection.models import RegistroColeta
count = RegistroColeta.objects.filter(id_microservico__in=[$(printf "'%s'," "${IDS[@]}" | sed 's/,$//')]).count()
print(count)
" 2>/dev/null | tail -1)

    if [[ "$PROCESSED" == "3" ]]; then
        break
    fi
    echo -e "    Aguardando... (${attempt}/15) — ${PROCESSED}/3 processados"
    sleep 1
done

if [[ "$PROCESSED" == "3" ]]; then
    success "Todas as 3 coletas foram processadas pelo Consumer!"
else
    echo -e "  ${RED}⚠ Apenas ${PROCESSED}/3 processadas. Verifique os logs: docker compose logs core-consumer${NC}"
fi

# ─── ETAPA 5: Verificar PostgreSQL ────────────────────────────────
separator
header "ETAPA 5 — Verificando dados no PostgreSQL (Core)"
echo ""

step "Registros de coleta com desconto calculado:"
echo ""

docker compose exec -T core python manage.py shell -c "
import django; django.setup()
from collection.models import RegistroColeta

coletas = RegistroColeta.objects.order_by('-data_hora_registro')[:3]
for c in reversed(list(coletas)):
    print(f'RESULT:  📦 {str(c.material):10s} | {str(c.peso_kg):>8s}kg | Desconto: {c.desconto_gerado}%')
" 2>/dev/null | grep '^RESULT:' | sed 's/^RESULT://'

echo ""
step "Saldo acumulado de desconto no IPTU por imóvel:"
echo ""

docker compose exec -T core python manage.py shell -c "
from program.models import SaldoPontos

for s in SaldoPontos.objects.all():
    barra = '█' * int(float(s.desconto_percentual))
    restante = '░' * (40 - int(float(s.desconto_percentual)))
    print(f'  🏠 {s.imovel.inscricao}')
    print(f'     Desconto IPTU: {s.desconto_percentual}% / 40%')
    print(f'     [{barra}{restante}]')
    print(f'     Total reciclado: {s.total_kg} kg no ciclo {s.ciclo}')
    print()
if not SaldoPontos.objects.exists():
    print('  (nenhum saldo registrado — imóvel não cadastrado)')
" 2>/dev/null | grep -v "objects imported"

# ─── ETAPA 6: Logs do Consumer ────────────────────────────────────
separator
header "ETAPA 6 — Logs do Core Consumer (processamento da fila)"
echo ""

LOGS=$(docker compose logs --tail 30 core-consumer 2>/dev/null | grep -iE "(processando|registrado|iniciando|aguardando|desconto|pts|erro)" | tail -8)
if [ -n "$LOGS" ]; then
    echo "$LOGS" | while IFS= read -r line; do
        echo -e "  ${CYAN}${line}${NC}"
    done
else
    docker compose logs --tail 8 core-consumer 2>/dev/null | while IFS= read -r line; do
        echo -e "  ${CYAN}${line}${NC}"
    done
fi

# ─── ETAPA 7: Resumo das regras de negócio ────────────────────────
separator
header "ETAPA 7 — Regras de negócio aplicadas"
echo ""

docker compose exec -T core python manage.py shell -c "
from program.business_rules import TAXA_DESCONTO, DESCONTO_MAXIMO

print('  Taxas de desconto no IPTU por kg de material:')
print()
nomes = {
    'papel': 'Papel/Papelão',
    'plastico': 'Plástico',
    'aluminio': 'Alumínio',
    'vidro': 'Vidro',
    'metal': 'Metal',
    'eletronico': 'Eletrônico',
}
for mat, taxa in TAXA_DESCONTO.items():
    print(f'    {nomes.get(mat, mat):20s} → {taxa}% por kg')
print()
print(f'  Teto máximo de desconto: {DESCONTO_MAXIMO}% por ciclo (ano)')
print(f'  Ajuste por moradores: fator de diluição (0.5 kg extra/pessoa)')
" 2>/dev/null | grep -v "objects imported"

# ─── Resumo final ─────────────────────────────────────────────────
separator
echo -e "${BOLD}${CYAN}"
echo "  ╔═══════════════════════════════════════════════════════╗"
echo "  ║              Demo concluída com sucesso!              ║"
echo "  ╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo -e "  ${BOLD}Fluxo demonstrado:${NC}"
echo ""
echo -e "  ${GREEN}1.${NC} POST /api/pesagens/ → Microserviço Django (porta 8001)"
echo -e "  ${GREEN}2.${NC} Microserviço persiste no ${CYAN}MongoDB${NC}"
echo -e "  ${GREEN}3.${NC} Microserviço publica na fila ${CYAN}RabbitMQ${NC}"
echo -e "  ${GREEN}4.${NC} Core Consumer consome da fila"
echo -e "  ${GREEN}5.${NC} Consumer calcula desconto e salva no ${CYAN}PostgreSQL${NC}"
echo -e "  ${GREEN}6.${NC} Saldo de desconto IPTU atualizado"
echo ""
echo -e "  ${MAGENTA}Painéis de administração:${NC}"
echo -e "    RabbitMQ: ${BLUE}http://localhost:15672${NC} (rabbit_user / rabbit_senha_local)"
echo -e "    MinIO:    ${BLUE}http://localhost:9001${NC} (minio_admin / minio_senha_local)"
echo -e "    Admin:    ${BLUE}http://localhost:8000/admin/${NC}"
echo ""
