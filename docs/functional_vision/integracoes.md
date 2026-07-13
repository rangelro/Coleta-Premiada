# Integrações do Sistema — Coleta Premiada

---

## 1. Integrações Internas (Entre Componentes do Sistema)

| De | Para | Meio | Dados | Direção |
|----|------|------|-------|---------|
| **Core (Django)** | **Microsserviço de Coleta** | RabbitMQ (fila `imoveis`) | Dados do imóvel: inscrição, endereço, coordenadas, proprietário, status | Assíncrono (Publisher → Consumer) |
| **Microsserviço de Coleta** | **Core (Django)** | RabbitMQ (fila `coletas`) | Dados da coleta: ID, imóvel, peso, timestamp | Assíncrono (Publisher → Consumer) |
| **Microsserviço de Coleta** | **Core (Django)** | HTTP (REST) | Validação de JWT e perfil do usuário (para endpoints de supervisor/gestor) | Síncrono |
| **Frontend (Next.js)** | **Core (Django)** | HTTP (REST) | Autenticação, imóveis, programas, usuários, consolidação, relatórios | Síncrono |
| **Frontend (Next.js)** | **Microsserviço de Coleta** | HTTP (REST) | Histórico de coletas (morador, supervisor, gestor), lista de imóveis | Síncrono |
| **App Mobile (React Native)** | **Microsserviço de Coleta** | HTTP (REST) | Login, coletas, imóveis próximos, sincronização | Síncrono |
| **Microsserviço de Coleta** | **MinIO** | S3-compatible HTTP | Fotos de evidência de coleta | Síncrono |

---

## 2. Integrações Externas

| Serviço | Função | Componente Consumidor | Tipo | Dados Trocados |
|---------|--------|-----------------------|------|----------------|
| **Google OAuth 2.0** | Autenticação social | Core (Backend) | Síncrono (HTTP) | Token de acesso, dados do perfil Google (nome, e-mail) |
| **OpenStreetMap (Nominatim)** | Geocodificação de endereços | Core (Backend) — via Celery | Assíncrono (HTTP, 1 req/s) | Endereço textual → Coordenadas (lat/lng) |
| **DeepSeek API** | Geração de relatórios narrativos com IA | Core (Backend) | Síncrono (HTTP, OpenAI-compatible) | Dados do programa + prompt → Relatório em linguagem natural |
| **LM Studio (Local LLM)** | Geração de relatórios narrativos (alternativa local) | Core (Backend) | Síncrono (HTTP, modelo `google/gemma-4-e2b`) | Dados do programa + prompt → Relatório em linguagem natural |

---

## 3. Integrações de Infraestrutura

| Serviço | Função | Consumido Por | Tipo |
|---------|--------|--------------|------|
| **PostgreSQL** | Banco de dados principal do Core | Core (Django) | Interno (ORM) |
| **MongoDB** | Banco de dados do microsserviço de coleta | Microsserviço de Coleta (Django) | Interno (ORM) |
| **RabbitMQ** | Mensageria entre Core e Microsserviço | Core (publisher/consumer) + Microsserviço (consumer/publisher) | Interno (AMQP) |
| **MinIO** | Armazenamento de objetos S3 | Microsserviço de Coleta | Interno (S3 API) |
| **Prometheus** | Coleta e armazenamento de métricas | Core + Microsserviço + Frontend + Infraestrutura | Scrape HTTP |
| **Grafana** | Visualização de métricas e dashboards | Prometheus (datasource) | Consulta |
| **node-exporter** | Métricas de infraestrutura (host) | Prometheus | Scrape |
| **cAdvisor** | Métricas de containers Docker | Prometheus | Scrape |
| **postgres-exporter** | Métricas do PostgreSQL | Prometheus | Scrape |
| **mongodb-exporter** | Métricas do MongoDB | Prometheus | Scrape |

---

## 4. Diagrama de Integrações (Visão Geral)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        REDE COMPARTILHADA DOCKER                        │
│                      (coleta-observability)                              │
│                                                                         │
│  ┌──────────────────────┐         ┌──────────────────────────────┐      │
│  │   FRONTEND (Next.js)  │         │    CORE (Django + PostgreSQL)│      │
│  │   Porta: 3000         │──REST──→│    Porta: 8001              │      │
│  │   Web: Morador,       │         │    - Autenticação           │      │
│  │   Supervisor, Gestor  │         │    - Programas              │      │
│  └──────────────────────┘         │    - Imóveis                │      │
│                                   │    - Pontuação              │      │
│   ┌─────────────────────┐         │    - Consolidação           │      │
│   │  APP MOBILE          │         │    - Contestações           │      │
│   │  (React Native)      │──REST──→│    - Auditoria              │      │
│   │  Coletor de campo    │         │    - Relatórios IA          │      │
│   └─────────────────────┘         └──────────┬───────────────────┘      │
│                                              │                          │
│                                    RabbitMQ  │  fila: imoveis           │
│                                    ┌─────────┴──────────┐               │
│                                    │     RabbitMQ        │               │
│                                    │  filas: imoveis,    │               │
│                                    │         coletas     │               │
│                                    └─────────┬──────────┘               │
│                                              │                          │
│                                    RabbitMQ  │  fila: coletas           │
│                                              │                          │
│  ┌──────────────────────────┐    ┌──────────┴───────────────────┐       │
│  │    MinIO (S3 Storage)    │    │  MICROSSERVIÇO DE COLETA     │       │
│  │    Fotos de evidência    │←───│  (Django + MongoDB)          │       │
│  └──────────────────────────┘    │  Porta: 8002                 │       │
│                                  │  - Coletas (offline-first)   │       │
│                                  │  - Imóveis (cache geoesp.)   │       │
│                                  │  - Sincronização             │       │
│                                  │  - Autenticação (coletores)  │       │
│  ┌──────────────────────────┐    └──────────────────────────────┘       │
│  │       OBSERVABILIDADE     │                                          │
│  │  ┌──────────┐ ┌────────┐ │                                          │
│  │  │Prometheus│ │Grafana │ │                                          │
│  │  │ :9090    │ │ :3001  │ │                                          │
│  │  └──────────┘ └────────┘ │                                          │
│  │  ┌──────────┐ ┌────────┐ │                                          │
│  │  │node-exp  │ │cAdvisor│ │                                          │
│  │  └──────────┘ └────────┘ │                                          │
│  └──────────────────────────┘                                          │
└─────────────────────────────────────────────────────────────────────────┘

                    LEGENDA:
                    ─── REST (Síncrono)
                    ─── RabbitMQ (Assíncrono)
                    ─── S3 (Storage)
                    ─── Scrape (Prometheus)
```
