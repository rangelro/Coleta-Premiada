# Infraestrutura e Execução

## Docker / Docker Compose

### Visão Geral dos Serviços

#### coleta-premiada/ (docker-compose.yml)

| Serviço | Imagem | Porta | Comando | Depende de |
|---|---|---|---|---|
| `core-db` | postgres:16-alpine | 5432 | — | — |
| `core` | coleta-premiada (dev/prod) | 8000 | runserver / gunicorn | core-db, rabbitmq |
| `core-celery` | coleta-premiada | — | celery worker | core-db, rabbitmq |
| `core-celery-beat` | coleta-premiada | — | celery beat | core-db, rabbitmq |
| `core-consumer` | coleta-premiada | — | consume_queue | core-db, rabbitmq |
| `rabbitmq` | rabbitmq:3-management-alpine | 5672, 15672 | — | — |
| `minio` | minio/minio | 9000, 9001 | — | — |
| `postgres-exporter` | prometheuscommunity/postgres-exporter | 9187 | — | core-db |
| `db-backup` | coleta-premiada-db-backup | — | cron backup.sh | core-db |

**Redes:** `core-network`, `storage-network`, `messaging-network`, `coleta-observability` (external), `coleta-shared` (external)
**Volumes:** `core-db-data`, `rabbitmq-data`, `minio-data`, `backup-data`

#### coleta-premiada-micro/ (docker-compose.yml)

| Serviço | Imagem | Porta | Comando |
|---|---|---|---|
| `ms-db` | mongo:7.0 | 27019:27017 | mongod |
| `rabbitmq-local` | rabbitmq:3-management-alpine | 5673:5672, 15673:15672 | — |
| `ms` | coleta-premiada-ms (dev) | 8002:8001 | runserver |
| `ms-consumer` | coleta-premiada-ms (dev) | — | consumir_imoveis |
| `mongodb-exporter` | percona/mongodb_exporter:0.40 | — | — |

**Portas não-padrão** para evitar conflitos com o stack completo (MongoDB 27019, RabbitMQ 5673/15673).
**Rede:** `ms-local-network` interna + `coleta-observability` (external)
**Extra host:** `host.docker.internal:host-gateway` para alcançar Core no host

#### coleta-premiada-frontend/ (docker-compose.yml)

| Serviço | Imagem | Porta | Comando |
|---|---|---|---|
| `frontend` | coleta-premiada-frontend (dev) | 3001 | next dev -p 3001 |

**Redes:** `coleta-shared` (external), `coleta-observability` (external)
**Volume mount:** bind mount do código com exclusão de node_modules e .next

#### coleta-premiada-observability/ (docker-compose.yml)

| Serviço | Imagem | Porta | Comando | Limites |
|---|---|---|---|---|
| `prometheus` | prom/prometheus:latest | 9090 | `--storage.tsdb.retention.time=30d --web.enable-lifecycle` | 0.5 CPU / 512MB RAM |
| `grafana` | grafana/grafana:latest | 3001:3000 | — | 0.5 CPU / 256MB RAM |
| `node-exporter` | prom/node-exporter:latest | 9100 | `pid: host` | 0.1 CPU / 64MB RAM |
| `cadvisor` | gcr.io/cadvisor/cadvisor:latest | 8080 | `privileged: true` | 0.2 CPU / 128MB RAM |

**Rede:** `coleta-observability` (criada aqui, usada como external pelos demais)

---

## Dockerfiles

### Core (Multi-stage)

```dockerfile
FROM python:3.12-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS development
COPY . .
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS production
COPY . .
RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", \
     "--workers", "4", "--timeout", "120"]
```

### Collection MS (Multi-stage)

```dockerfile
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS development
COPY . .
EXPOSE 8001
CMD ["python", "manage.py", "runserver", "0.0.0.0:8001"]

FROM base AS production
COPY . .
EXPOSE 8001
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8001", \
     "--workers", "4", "--timeout", "120"]
```

### Frontend (Multi-stage)

```dockerfile
FROM node:20-alpine AS base
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --frozen-lockfile

FROM base AS development
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

FROM base AS builder
COPY . .
RUN npm run build

FROM node:20-alpine AS production
ENV NODE_ENV=production
WORKDIR /app
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
```

Uso de `output: "standalone"` no `next.config.ts` para imagem de produção mínima.

---

## Ordem de Inicialização

1. **coleta-premiada-observability** — `docker compose up -d`
   - Cria rede `coleta-observability`
   - Inicia Prometheus, Grafana, Node Exporter, cAdvisor

2. **coleta-premiada** (Core) — `docker compose up -d`
   - Inicia PostgreSQL, RabbitMQ, MinIO
   - Aplica migrações Django
   - Inicia Core API, Celery Worker, Celery Beat, Consumer, Backup

3. **coleta-premiada-micro** (MS) — `docker compose up -d`
   - Conecta à rede `coleta-observability`
   - Inicia MongoDB, RabbitMQ local (portas alternativas)
   - Aplica migrações Django (MongoDB)
   - Inicia MS API e Consumer

4. **coleta-premiada-frontend** — `docker compose up -d`
   - Conecta às redes compartilhadas
   - Inicia Next.js dev server

---

## Ambientes

### Desenvolvimento

| Característica | Configuração |
|---|---|
| **Core DEBUG** | `True` |
| **Core servidor** | `manage.py runserver` (hot reload) |
| **MS servidor** | `manage.py runserver` (hot reload) |
| **Frontend** | `next dev` (HMR) |
| **Mobile** | `expo start` (com QR code / emulador) |
| **CORS** | `CORS_ALLOW_ALL_ORIGINS=True` (DEBUG) |
| **MinIO** | Local, porta 9000 |
| **RabbitMQ** | Local, porta 5672 (ou 5673 no MS standalone) |

Docker Compose de desenvolvimento usa bind mounts para refletir alterações de código em tempo real.

### Produção (implícito pelo Dockerfile)

| Característica | Configuração |
|---|---|
| **Core servidor** | Gunicorn 4 workers, 120s timeout |
| **MS servidor** | Gunicorn 4 workers, 120s timeout |
| **Frontend** | `next build` + `node server.js` (standalone) |
| **CORS** | `CORS_ALLOWED_ORIGINS` explícito |
| **DEBUG** | `False` |
| **Static files** | Whitenoise serve diretamente pelo Django |

Não há configuração explícita de staging ou produção — os ambientes diferem apenas pelo Dockerfile target e variáveis de ambiente.

---

## CI/CD

### Core (GitHub Actions)

```yaml
name: CI
on: [push, pull_request]
branches: [main, develop, temp_develop]
jobs:
  check-ci:
    steps:
      - uses: actions/checkout@v4
      - name: Create shared network
        run: docker network create coleta-observability || true
      - name: Setup env
        run: cp .env.example .env
      - name: Install project
        run: make up
      - name: Check Django
        run: make check
      - name: Check migrations
        run: make migrations-check
      - name: Apply migrations
        run: make migrate-check
```

### Frontend (GitHub Actions)

Dois workflows separados para `develop` e `main`:
- `npm ci` → `npm run lint` → `npm run build`
- No `main`: adicionalmente build + execução da imagem Docker de produção como smoke test

---

## Makefile (Core)

```makefile
up:         docker compose up -d
build:      docker compose build
down:       docker compose down
down-vol:   docker compose down -v
logs:       docker compose logs -f --tail=100
stop:       docker compose stop

migrations: docker compose exec core python manage.py makemigrations
migrate:    docker compose exec core python manage.py migrate
createsuperuser: docker compose exec core python manage.py createsuperuser
shell:      docker compose exec core bash

db-backup:  docker compose exec db-backup /scripts/backup.sh
db-restore: docker compose exec db-backup /scripts/restore.sh $(FILE)

check:              docker compose run --rm core python manage.py check
migrations-check:   docker compose run --rm core python manage.py makemigrations --check --dry-run
migrate-check:      docker compose run --rm core python manage.py migrate

monitoring-up:      docker compose -f docker-compose.monitoring.yml up -d
monitoring-down:    docker compose -f docker-compose.monitoring.yml down
monitoring-logs:    docker compose -f docker-compose.monitoring.yml logs -f --tail=100
monitoring-smoke:   bash scripts/smoke_test_monitoring.sh
```

---

## Scripts e Comandos Django

### Core (Management Commands)

| Comando | Uso |
|---|---|
| `consume_queue` | Consumer RabbitMQ da fila `coletas` (serviço `core-consumer`) |
| `geocodificar_imoveis` | Geocoding em lote com opção `--dry-run` |
| `passo_admin` | Seed de dados de teste (idempotente) |
| `test_llm_report` | Teste manual da integração DeepSeek |
| `test_local_llm_report` | Teste manual da integração LM Studio |

### Collection MS (Management Commands)

| Comando | Uso |
|---|---|
| `consumir_imoveis` | Consumer RabbitMQ da fila `imoveis` com auto-reconnect (serviço `ms-consumer`) |
| `reenviar_coletas` | Retry de sincronização de coletas com falha |

### Mobile

Scripts Expo padrão: `expo start`, `expo start --android`, `expo start --ios`, `expo start --web`

---

## Prometheus Metrics

### Scrape Targets

| Job | Target | Path | Port |
|---|---|---|---|
| `django-core` | `core:8000` | `/metrics` | 8000 |
| `django-ms-dev` | `ms-dev:8001` | `/metrics` | 8001 |
| `postgres` | `postgres-exporter:9187` | `/metrics` | 9187 |
| `mongodb` | `mongodb-exporter:9216` | `/metrics` | 9216 |
| `rabbitmq` | `rabbitmq:15692` | `/metrics` | 15692 |
| `node` | `node-exporter:9100` | `/metrics` | 9100 |
| `cadvisor` | `cadvisor:8080` | `/metrics` | 8080 |

### Alertas

| Alerta | Expressão | Severidade |
|---|---|---|
| PGConnectionsHigh | `sum(pg_stat_database_numbackends) / pg_settings_max_connections > 0.8` por 2min | warning |
| PGSlowQuery | `pg_long_running_queries_count > 0` por 1min | warning |
| DiskSpaceHigh | disco > 80% por 5min | critical |
| RabbitMQQueueHigh | `rabbitmq_queue_messages_ready > 1000` por 5min | warning |

Sem Alertmanager configurado — alertas visíveis apenas na UI do Prometheus.
