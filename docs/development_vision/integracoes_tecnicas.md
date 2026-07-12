# Integrações Técnicas

## Dependências Externas

### Banco de Dados

| Serviço | Tecnologia | Uso | Responsável |
|---|---|---|---|
| Core DB | PostgreSQL 16 | Dados do programa (usuários, imóveis, coletas, pontuação, auditoria) | Core (coleta-premiada/) |
| MS DB | MongoDB 7 | Dados do microsserviço (coletores, imóveis, coletas offline) | Collection MS (coleta-premiada-micro/) |
| Mobile DB | SQLite (expo-sqlite) | Cache offline de coletas e imóveis | App Mobile (coleta-premiada-app/) |

### Mensageria

| Tecnologia | Uso | Gerenciado por |
|---|---|---|
| RabbitMQ 3 (management) | Filas `imoveis` (Core → MS) e `coletas` (MS → Core) | Core (docker-compose) + MS (docker-compose standalone) |
| Plugin Prometheus RabbitMQ | Métricas na porta 15692 | Habilitado em `enabled_plugins` |

### Storage

| Tecnologia | Uso | Gerenciado por |
|---|---|---|
| MinIO (S3-compatible) | Upload de fotos de evidência de coleta | Core (docker-compose) |

### Observabilidade

| Tecnologia | Uso | Gerenciado por |
|---|---|---|
| Prometheus | Coleta e armazenamento de métricas | Observability (coleta-premiada-observability/) |
| Grafana | Dashboards de visualização | Observability |
| Node Exporter | Métricas do host (CPU, disco, memória) | Observability |
| cAdvisor | Métricas de container | Observability |
| PostgreSQL Exporter | Métricas do banco Core | Core (docker-compose) |
| MongoDB Exporter | Métricas do banco MS | MS (docker-compose standalone) |

### APIs Externas

| API | Uso | Configuração | Fallback |
|---|---|---|---|
| **DeepSeek API** (OpenAI-compatível) | Geração de relatórios narrativos LLM | `DEEPSEEK_API_KEY` | LM Studio local |
| **LM Studio** (local) | LLM local para relatórios | `LOCAL_LLM_BASE_URL=http://host.docker.internal:1234` | — |
| **Google OAuth2** | Login social | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Login email/senha |
| **Nominatim (OpenStreetMap)** | Geocoding de endereços de imóveis | `NOMINATIM_USER_AGENT` | Nenhum (falha visível) |

---

## Configuração por Ambiente

### Core (.env.example)

```ini
# PostgreSQL
POSTGRES_DB=coleta_premiada
POSTGRES_USER=postgres
POSTGRES_PASSWORD=troque_esta_senha

# RabbitMQ
RABBITMQ_DEFAULT_USER=guest
RABBITMQ_DEFAULT_PASS=troque_esta_senha

# MinIO
MINIO_ROOT_USER=minio_admin
MINIO_ROOT_PASSWORD=troque_esta_senha
MINIO_ACCESS_KEY=minio_admin
MINIO_SECRET_KEY=troque_esta_senha
MINIO_BUCKET_NAME=coletas
MINIO_USE_HTTPS=False

# MongoDB
MONGO_INITDB_DATABASE=coleta_db
MONGO_USER=coleta_user
MONGO_PASSWORD=troque_esta_senha

# Django
DJANGO_SECRET_KEY=troque_esta_chave_super_secreta_minimo_50_chars
DEBUG=True

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8001
NEXT_PUBLIC_APP_NAME=Coleta Premiada

# Grafana
GF_ADMIN_USER=admin
GF_ADMIN_PASSWORD=troque_esta_senha

# Google OAuth2
GOOGLE_CLIENT_ID=seu_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=seu_client_secret

# Nominatim
NOMINATIM_USER_AGENT="coleta-premiada/1.0 (youremail@example.com)"

# Backup
BACKUP_CRON_SCHEDULE="0 2 * * *"
BACKUP_KEEP_DAILY=7
BACKUP_KEEP_WEEKLY=4
BACKUP_WEEKLY_DAY=7
```

### Collection MS (.env.example)

```ini
# Django
DJANGO_SECRET_KEY=...
DEBUG=True
CORE_JWT_SECRET_KEY=...       # Mesma chave do Core (DJANGO_SECRET_KEY)

# MongoDB
MONGO_INITDB_DATABASE=coleta_db
MONGO_USER=coleta_user
MONGO_PASSWORD=senha123
MONGO_HOST=localhost
MONGO_PORT=27017

# RabbitMQ
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_DEFAULT_USER=guest
RABBITMQ_DEFAULT_PASS=guest

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=coletas
MINIO_USE_HTTPS=False

# Core API
CORE_API_URL=http://host.docker.internal:8001
```

### Frontend (.env.example)

```ini
# Servidor
CORE_API_URL=http://localhost:8001
COLLECTION_API_URL=http://localhost:8002

# Cliente (browser)
NEXT_PUBLIC_API_URL=http://localhost:3001

# JWT (em segundos)
JWT_ACCESS_COOKIE_TTL=28800     # 8 horas
JWT_REFRESH_COOKIE_TTL=604800   # 7 dias

# Google OAuth
NEXT_PUBLIC_GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

### Mobile

API URL **hardcoded** em `services/api.ts`:
```typescript
export const API_BASE_URL = 'http://192.168.0.14:8002/api/';
```

Não há suporte a variáveis de ambiente ou arquivo `.env`.

---

## Redes Docker

### Rede Compartilhada `coleta-observability`

Criada pelo repositório de observabilidade, declarada como `external: true` nos demais:

| Serviço | Domínio na Rede | Métricas |
|---|---|---|
| Core API | `core:8000` | `/metrics` (django-prometheus) |
| Collection MS | `ms-dev:8001` | `/metrics` (django-prometheus) |
| PostgreSQL Exporter | `postgres-exporter:9187` | pg_exporter |
| MongoDB Exporter | `mongodb-exporter:9216` | mongodb_exporter |
| RabbitMQ | `rabbitmq:15692` | Built-in Prometheus |
| Node Exporter | `node-exporter:9100` | host metrics |
| cAdvisor | `cadvisor:8080` | container metrics |
| Frontend | `frontend:3001` | via cAdvisor (sem django-prometheus) |

---

## Sistema de Pontuação (Regra de Negócio)

```
pontos_coleta = peso_kg × ConstantePontuacao.pontos_por_kg
desconto_percentual = pontos_coleta / RegraPrograma.pontos_por_real
desconto_aplicado = min(desconto_percentual, DESCONTO_MAXIMO - desconto_atual_acumulado)
```

- **DESCONTO_MAXIMO:** 40% (hardcoded em `business_rules.py`)
- **ConstantePontuacao:** Singleton editável por supervisor
- **RegraPrograma:** Configurável por programa (OneToOne com Programa)
- **Consolidação:** Processo manual disparado por gestor, calcula saldo de todos os imóveis

---

## Relatórios LLM

Dual-mode suportado:

### Modo Cloud (DeepSeek API)
```python
client = openai.OpenAI(
    api_key=settings.DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[...]
)
```

### Modo Local (LM Studio)
```python
client = openai.OpenAI(
    base_url=settings.LOCAL_LLM_BASE_URL,  # http://host.docker.internal:1234/v1
    api_key="not-needed"
)
response = client.chat.completions.create(
    model=settings.LOCAL_LLM_MODEL,  # "google/gemma-4-e2b"
    messages=[...]
)
```

- Fallback automático: se `DEEPSEEK_API_KEY` não estiver configurada, usa LM Studio
- Dados extraídos via `LLMReportService.extrair_dados_do_banco()` (agregações SQL)
- Tipos de relatório: `participacao`, `impacto`, `ranking`, `auditoria`

---

## Backup

Serviço dedicado `db-backup` no Core:
- **Base:** Python 3.12-slim com PostgreSQL client
- **Mecanismo:** `pg_dump` do banco Core
- **Agendamento:** Cron (configurável via `BACKUP_CRON_SCHEDULE`, default 2h diário)
- **Retenção:** Configurável (daily/weekly)
- **Volume:** `backup-data` montado para persistência
- **Restauração:** Script `restore.sh` com confirmação
