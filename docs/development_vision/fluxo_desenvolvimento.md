# Fluxo de Desenvolvimento

## Como Rodar o Sistema Localmente

### Pré-requisitos

- Docker + Docker Compose
- Node.js 20+ (para frontend fora do Docker)
- Expo CLI (para mobile)
- Python 3.12 (para desenvolvimento local dos backends)

### Ordem de Inicialização (Docker Compose)

```bash
# 1. Observabilidade (deve ser primeiro — cria rede compartilhada)
cd coleta-premiada-observability
cp .env.example .env
docker compose up -d

# 2. Core
cd ../coleta-premiada
cp .env.example .env
make up           # docker compose up -d
make migrate      # Aplica migrações Django

# 3. Collection MS
cd ../coleta-premiada-micro
cp .env.example .env
docker compose up -d
docker compose exec ms python manage.py migrate

# 4. Frontend
cd ../coleta-premiada-frontend
cp .env.example .env
docker compose up -d
```

**Importante:** O serviço `ms` do microservice usa `extra_hosts: "host.docker.internal:host-gateway"` para alcançar o Core no host. Em desenvolvimento standalone (fora do Docker), ajustar `CORE_API_URL` e `MONGO_HOST` no `.env`.

### Mobile (fora do Docker)

```bash
cd coleta-premiada-app
npm install
npx expo start
```

O mobile aponta diretamente para o Collection MS via IP da rede local (`API_BASE_URL = 'http://192.168.0.14:8002/api/'`). Ajustar o IP no arquivo `services/api.ts` conforme necessário.

---

## Processo de Build

### Core (Django)

```bash
# Desenvolvimento (hot reload via runserver)
make up

# Produção
docker compose build core  # target: production
```

Build produz imagem com `gunicorn` servindo na porta 8000. Static files servidos via WhiteNoise.

### Collection MS (Django)

```bash
# Desenvolvimento (hot reload)
docker compose up -d ms

# Produção
docker compose build ms  # target: production
```

Build produz imagem com `gunicorn` servindo na porta 8001.

### Frontend (Next.js)

```bash
# Desenvolvimento (HMR)
docker compose up -d frontend

# Produção
docker compose build frontend  # target: production
```

Usa `output: "standalone"` para imagem mínima. Build produz `.next/standalone/` com apenas os arquivos necessários para runtime.

### Mobile (Expo)

```bash
# Build EAS (Expo Application Services) — produção
npx eas build --platform android  # ou ios

# Preview local
npx expo export --platform web
```

---

## Migrações de Banco

### Core (PostgreSQL)

```bash
# Criar migrações (após alterar models.py)
make migrations

# Aplicar migrações
make migrate

# Verificar consistência (CI)
make migrations-check   # makemigrations --check --dry-run
make migrate-check      # migrate (valida sem alterar)
```

### Collection MS (MongoDB)

```bash
# Aplicar migrações
docker compose exec ms python manage.py migrate

# Migrações específicas
docker compose exec ms python manage.py migrate coleta 0007

# Criar migrações
docker compose exec ms python manage.py makemigrations
```

**Nota:** O MongoDB via `django-mongodb-backend` não suporta todas as features do Django ORM relacional. Migrações para `admin`, `auth` e `contenttypes` foram customizadas em `mongo_migrations/`.

### Frontend

Sem migrações — aplicação stateless. Dados são gerenciados exclusivamente via APIs.

### Mobile

Schema SQLite inicializado em `services/database/db.ts`:
```typescript
export async function initDatabase(): Promise<void> {
  const db = await getDatabase();
  await db.execAsync(`
    CREATE TABLE IF NOT EXISTS coletas (
      offline_id TEXT PRIMARY KEY,
      imovel_id TEXT NOT NULL,
      endereco TEXT,
      morador TEXT,
      peso_total_kg REAL NOT NULL,
      observacoes TEXT,
      foto_base64 TEXT,
      data_hora TEXT NOT NULL,
      enviada INTEGER DEFAULT 0,
      erro TEXT,
      criado_em TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS imoveis_cache (...);
    CREATE TABLE IF NOT EXISTS mapas_offline (...);
  `);
}
```

Schema versionado pelo código — sem sistema de migrations. Alterações de schema exigem deletar o banco local.

---

## Testes

### Core

```bash
# Reports (único app com testes reais)
docker compose exec core python manage.py test reports

# Todos os apps (a maioria são stubs vazios)
docker compose exec core python manage.py test
```

**Cobertura:**
| App | Status | Quantidade |
|---|---|---|
| `accounts` | Stub vazio | — |
| `collection` | Stub vazio | — |
| `program` | Stub vazio | — |
| `reports` | **Implementados** | 22 testes (4 classes) |

Testes de reports cobrem:
- `LLMReportService.extrair_dados_do_banco()` — métricas gerais, top bairros, média desconto, período vazio
- `LLMReportService.gerar_relatorio_narrativo()` — estrutura do retorno, prompt, API key ausente (mock)
- `GenerateReportViewTests` — permissão gestor, negação morador, tipo inválido, período invertido, falha LLM
- `ReportHistoryViewTests` — listagem, filtros, permissão supervisor, campos de retorno

### Collection MS

```bash
# Teste de integração (requer Core + MS rodando)
python test_integration.py
```

Teste de 653 linhas que valida:
1. Health checks (MongoDB, PostgreSQL, RabbitMQ, APIs)
2. Fluxo Core → MS (cria imóvel no Core → verifica no MS via RabbitMQ)
3. Fluxo MS → Core (cria coleta no MS → verifica no Core via RabbitMQ)
4. Cross-validação de status de sincronização

### Frontend

Sem testes. `package.json` não possui Jest, React Testing Library ou qualquer framework de teste.

### Mobile

Sem testes. Nenhum framework de teste nas dependências, nenhum arquivo `.test.ts` ou `__tests__/`.

---

## Scripts Úteis

### Core

```bash
# Acessar shell do container
make shell

# Criar superusuário
make createsuperuser

# Backup do banco
make db-backup

# Restore do banco
make db-restore FILE=backup_20260711_020000.sql

# Logs
make logs

# Parar tudo
make down

# Parar e limpar volumes
make down-vol
```

### Collection MS

```bash
# Teste manual de filas RabbitMQ (CLI interativa)
python teste_mq.py
```

### Geral

```bash
# Smoke test da monitoria
bash coleta-premiada/scripts/smoke_test_monitoring.sh
```

---

## Estrutura de Branches (GitHub)

| Branch | Uso |
|---|---|
| `main` | Produção |
| `develop` | Desenvolvimento ativo |
| `temp_develop` | Branch temporária de desenvolvimento |

CI roda em push/PR para todas as três branches.

---

## Problemas Conhecidos no Fluxo de Desenvolvimento

1. **API URL hardcoded no mobile** — sem suporte a `.env`, todo desenvolvedor precisa alterar `services/api.ts` manualmente
2. **Portas conflitantes** — MS usa portas não-padrão (MongoDB 27019, RabbitMQ 5673) que precisam ser mapeadas mentalmente
3. **Sem testes no frontend/mobile** — impossibilidade de validar regressão automaticamente
4. **Dependência de `host.docker.internal`** — não funciona em Linux sem `extra_hosts` configurado
5. **Migrations MongoDB** — o `makemigrations --check --dry-run` do Core não se aplica ao MS, aumentando risco de inconsistência
