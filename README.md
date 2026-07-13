# Coleta Premiada — Core (Monolito)

## Proposito do Sistema

O **Core** e o coracao do ecossistema **Coleta Premiada** — uma plataforma de incentivo a coleta seletiva e reciclagem. Ele centraliza o cadastro e a gestao de usuarios (moradores, coletores, gestores e supervisores), as regras de negocio dos programas de incentivo (calculo de pontos, metas, descontos no IPTU) e a consolidacao dos dados de coleta recebidos do microservico de campo.

Na arquitetura geral, o Core atua como orquestrador:

1. **Cadastra imoveis** no PostgreSQL e publica eventos na fila `imoveis` (RabbitMQ) para que o microservico de coleta os replique no MongoDB.
2. **Consome eventos** da fila `coletas` (via Celery) — cada coleta registrada em campo pelo coletor gera um evento que o Core processa para creditar pontos ao morador.
3. **Serve o portal web** (Next.js) e **o app mobile** (Expo) via API REST, alem de expor o Django Admin para gestao interna.
4. **Mantem trilhas de auditoria** (`custom_audit`) em todas as acoes sensiveis (login, alteracao de pontos, contestacoes, etc.).
5. **Dispara emails transacionais** (confirmacao de cadastro, notificacao de metas, redefinicao de senha) e integra **OAuth2 via Google**.

### Perfis de Usuario

| Perfil | Descricao |
|---|---|
| **Morador** | Cidadao que acumula pontos conforme materiais reciclaveis sao coletados. Acompanha pontos, metas e contesta via portal web. |
| **Coletor** | Agente de campo. Usa o app mobile (conectado ao MS de Coleta) para registrar coletas. No Core, aparece como entidade de referencia. |
| **Gestor** | Analisa engajamento com dashboards, rankings e relatorios no portal web. |
| **Supervisor** | Administrador do sistema com acesso ao Django Admin e relatorios avancados. |

---

## Tecnologias

### Stack Principal

| Camada | Tecnologia | Versao |
|---|---|---|
| **Linguagem** | Python | 3.12 |
| **Framework Web** | Django | 6.0 |
| **API REST** | Django REST Framework | 3.17 |
| **Banco de Dados** | PostgreSQL | 16 (Alpine) |
| **Filas / Mensageria** | RabbitMQ + Celery | 3-management-alpine / 5.4 |
| **Object Storage** | MinIO (S3-compatible) | latest |
| **Autenticacao** | `djangorestframework-simplejwt` (JWT + refresh token rotativo) | 5.5 |
| **OAuth2 Social** | Google OAuth2 | — |

### Bibliotecas e Suas Funcoes

| Biblioteca | Funcao |
|---|---|
| `djangorestframework` + `simplejwt` | API RESTful com autenticacao JWT (access/refresh tokens, blacklist) |
| `celery` | Processamento assincrono — consume a fila `coletas` e credita pontos |
| `pika` | Cliente RabbitMQ para publicar eventos na fila `imoveis` |
| `psycopg2-binary` | Driver PostgreSQL para Django |
| `geopy` | Geocodificacao de enderecos via Nominatim (OpenStreetMap) |
| `minio` | SDK para upload/download de fotos de coleta no MinIO |
| `django-cors-headers` | Habilita CORS para o frontend Next.js (`localhost:3001`) |
| `gunicorn` | Servidor WSGI de producao (4 workers, timeout 120s) |
| `whitenoise` | Serve arquivos estaticos (Django Admin, DRF Browsable API) sem servidor web externo |
| `django-prometheus` | Exporta metricas para o Prometheus (`/metrics`) |
| `openai` | Cliente para LLM (DeepSeek API ou LM Studio local) para funcionalidades de IA |

### Estrutura de Apps Django

```
core/
├── accounts/        # Model Usuario customizado (perfis: Morador, Gestor, Supervisor),
│                    #   autenticacao JWT, Google OAuth2, confirmacao de email,
│                    #   permissoes por perfil (scoping)
├── collection/      # Model Imovel, geocodificacao via Nominatim, sinais que
│                    #   publicam eventos na fila imoveis (RabbitMQ)
├── program/         # Programas de incentivo, calculo de pontos, metas, IPTU
├── reports/         # Dashboards, rankings e relatorios para gestores
├── messaging/       # Abstracao de mensageria — consumidores e produtores RabbitMQ
├── custom_audit/    # Middleware + signals que registram auditoria de acoes
│                    #   sensiveis no PostgreSQL (via models Django)
└── config/          # settings.py, urls.py, celery.py, wsgi.py, asgi.py
```

### Servicos Docker (docker-compose.yml)

| Servico | Descricao |
|---|---|
| `core-db` | PostgreSQL 16 com `pg_stat_statements` habilitado para metricas |
| `core` | API Django servida via Gunicorn (prod) ou `runserver` (dev) |
| `core-celery` | Worker Celery — processa creditos de pontos e tarefas assincronas |
| `core-celery-beat` | Scheduler Celery — tarefas periodicas |
| `core-consumer` | Consumidor da fila `coletas` (RabbitMQ → PostgreSQL) |
| `rabbitmq` | Broker de mensagens com plugin de management + metricas Prometheus |
| `minio` | Object Storage S3-compatible para fotos de coleta |
| `postgres-exporter` | Exporta metricas do PostgreSQL para o Prometheus |
| `db-backup` | Backup agendado (cron) do PostgreSQL com retencao diaria/semanal e upload offsite opcional para MinIO |
| `postgres-maintenance` | Manutencao automatizada: limpeza de logs, VACUUM, REINDEX periodicos |

### Redes Docker

| Rede | Participantes |
|---|---|
| `core-network` | core-db, core, core-celery*, core-consumer, db-backup, postgres-exporter |
| `messaging-network` | rabbitmq, core, core-celery, core-consumer |
| `storage-network` | minio, core |
| `coleta-observability` | Externa — conecta metricas ao stack Prometheus/Grafana |
| `coleta-shared` | Externa — compartilhada com microservico de coleta e frontend |

---

## Instalacao

### Pre-requisitos

- [Docker](https://docs.docker.com/engine/install/) e [Docker Compose](https://docs.docker.com/compose/install/)
- [Git](https://git-scm.com/)

### Passo a Passo

**1. Clone o repositorio:**

```bash
git clone https://github.com/rangelro/Coleta-Premiada.git
cd Coleta-Premiada
```

**2. Configure as variaveis de ambiente:**

```bash
cp .env.example .env
```

Edite o `.env` e **substitua todas as credenciais** (`POSTGRES_PASSWORD`, `DJANGO_SECRET_KEY`, `RABBITMQ_DEFAULT_PASS`, `MINIO_ROOT_PASSWORD`, etc.). O arquivo `.env.example` contem comentarios explicativos para cada variavel.

**3. Suba o stack de observabilidade primeiro** (se ainda nao estiver rodando):

```bash
cd ../coleta-observability && docker compose up -d && cd ../Coleta-Premiada
```

**4. Suba os containers do Core:**

```bash
docker compose up -d
```

Isso inicia: PostgreSQL, RabbitMQ, MinIO, a API Django (porta `8001`), workers Celery e backup.

**5. Execute as migracoes do banco:**

```bash
make migrate
# ou: docker compose exec core python manage.py migrate
```

**6. Crie um superusuario (opcional, para acessar o Django Admin):**

```bash
make createsuperuser
# ou: docker compose exec core python manage.py createsuperuser
```

**7. Acesse a aplicacao:**

| Recurso | URL |
|---|---|
| **API REST** | `http://localhost:8001/api/` |
| **Django Admin** | `http://localhost:8001/admin/` |
| **MinIO Console** | `http://localhost:9001` |
| **RabbitMQ Management** | `http://localhost:15672` |

### Comandos Uteis (via Makefile)

```bash
make up              # Sobe os containers
make down            # Derruba os containers
make logs            # Logs dos containers (tail -f)
make build           # Rebuild das imagens
make migrations      # Gera novas migracoes
make migrate         # Aplica migracoes
make shell           # Abre bash no container core
make db-backup       # Dispara backup manual do PostgreSQL
make down-vol        # Derruba TUDO inclusive volumes (PERDA DE DADOS!)
make monitoring-up   # Sobe stack de observabilidade
```

### Ordem de Inicializacao do Ecossistema

```
1. coleta-observability/     docker compose up -d   # Metricas/logs centralizados
2. Coleta-Premiada/          docker compose up -d   # Core (este repositorio)
3. cp-collection-ms/         docker compose up -d   # Microservico de Coletas
4. coleta-premiada-frontend/ docker compose up -d   # Portal Web
```

> O app mobile (`coleta-premiada-app`) e executado diretamente via `npx expo start`.

---

## Documentacao Adicional

- [API Mapping](API_MAPPING.md) — Mapeamento completo dos endpoints REST
- [Endpoints](ENDPOINTS.md) — Detalhamento de cada endpoint
- [Especificacao de Auditoria — Backend](SPEC_AUDITORIA_BACKEND.md)
- [Especificacao de Auditoria — Frontend](SPEC_AUDITORIA_FRONTEND.md)
- [Especificacao de Auditoria — Microservico](SPEC_AUDITORIA_MICROSERVICO.md)
- [Especificacao de Email](SPEC_EMAIL.md)
- [Diagrama de Arquitetura](docs/diagrams/diagrama-arquiterura.png)
- [Wiki do Projeto](https://github.com/rangelro/Coleta-Premiada/wiki)
