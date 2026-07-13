# Arquitetura Geral do Sistema

## Tipo de Arquitetura: Híbrida (Monólito + Microsserviço + Event-Driven)

O sistema **Coleta Premiada** adota uma arquitetura **híbrida**, combinando um monólito modular (Core) com um
microsserviço especializado (Collection MS), comunicação assíncrona via mensageria e sincronismo HTTP entre
as camadas. Não há service mesh, API gateway centralizado ou orquestração de containers como Kubernetes.

---

## Repositórios e Responsabilidades

### coleta-premiada/ (Core — Django + PostgreSQL)
**Função:** Backend principal, domínio de gestão do programa de reciclagem.

- **Domínios:** Usuários, perfis, roles, cidades (`accounts`) — Imóveis, programas, regras, consolidação, pontuação (`program`) — Registros de coleta, evidências, contestações (`collection`) — Relatórios LLM (`reports`) — Auditoria completa (`custom_audit`)
- **Persistência:** PostgreSQL 16
- **Filas:** Producer e Consumer RabbitMQ (pika)
- **Tarefas Assíncronas:** Celery (geocoding, agendamentos)
- **Monitoria:** django-prometheus (métricas em `/metrics`)
- **Exposição:** Gunicorn na porta 8000

### coleta-premiada-micro/ (Collection MS — Django + MongoDB)
**Função:** Microsserviço de campo — gerencia agentes de coleta, imóveis sincronizados e registros de coleta com suporte offline.

- **Domínios:** Autenticação de agentes coletores (`coletores`) — Gestão de imóveis e coletas com geolocalização (`coleta`)
- **Persistência:** MongoDB 7 (com backend django-mongodb-backend)
- **Filas:** Producer (`coletas`) e Consumer (`imoveis`) RabbitMQ
- **Storage:** MinIO (upload de fotos de coleta)
- **Monitoria:** django-prometheus (métricas em `/`)
- **Exposição:** Gunicorn na porta 8001

### coleta-premiada-frontend/ (Frontend Web — Next.js 16)
**Função:** Interface web administrativa e do morador.

- **Framework:** Next.js 16 (App Router), React 19, TypeScript
- **Estilização:** Tailwind CSS 4 + shadcn/ui
- **Comunicação:** Axios com dois clientes distintos (Core API e Collection MS)
- **Autenticação:** JWT em httpOnly cookies com middleware de refresh automático
- **Renderização:** Server Components (padrão), Client Components para interatividade
- **Porta:** 3001

### coleta-premiada-app/ (Mobile — React Native / Expo)
**Função:** Aplicativo mobile do agente de coleta, com operação offline-first.

- **Framework:** React Native 0.81.5 + Expo SDK 54
- **Roteamento:** Expo Router (file-based)
- **Banco local:** SQLite (expo-sqlite) para cache offline
- **Autenticação:** JWT armazenado em SecureStore
- **Comunicação:** Axios único apontando para Collection MS (porta 8002)
- **Funcionalidades offline:** Registro de coleta sem conectividade, sincronização automática em background

### coleta-premiada-observability/ (Observabilidade — Prometheus + Grafana)
**Função:** Stack centralizada de métricas para todo o ecossistema.

- **Componentes:** Prometheus (coleta + armazenamento), Grafana (visualização + dashboards), Node Exporter (métricas do host), cAdvisor (métricas de container)
- **Rede:** Cria a rede `coleta-observability` usada como `external` pelos demais repositórios
- **Portas:** Prometheus 9090, Grafana 3001
- **Integração:** Scrape de métricas via django-prometheus, postgres-exporter, mongodb-exporter, RabbitMQ plugin

---

## Fronteiras entre Serviços

```
┌───────────────────────────────────────────────────────────────────┐
│                    coleta-premiada/ (Core)                         │
│   PostgreSQL 16  │  RabbitMQ (pub)  │  Celery  │  Gunicorn:8000   │
│                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │
│  │ accounts │ │ program  │ │collection│ │custom_aud│ │reports │  │
│  └─────┬────┘ └─────┬────┘ └────┬─────┘ └──────────┘ └───┬────┘  │
│        │             │           │                         │       │
│        └─────────────┴───────────┴─────────────────────────┘       │
│                          │  messaging/ (pika)                      │
│                    ┌─────┴──────┐                                  │
│                    │  imoveis   │  (publica ao salvar Imovel)      │
│                    └─────┬──────┘                                  │
│                    ┌─────┴──────┐                                  │
│                    │  coletas   │  (consome registros de coleta)   │
│                    └────────────┘                                  │
└────────────────────────┬──────────────────────────────────────────┘
                         │ RabbitMQ
                         ▼
┌───────────────────────────────────────────────────────────────────┐
│               coleta-premiada-micro/ (Collection MS)               │
│   MongoDB 7  │  MinIO  │  RabbitMQ (consumer)  │  Gunicorn:8001   │
│                                                                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │ coletores│ │  coleta  │ │ services │ │ storage  │             │
│  │  (auth)  │ │(imoveis, │ │ (fila,   │ │ (MinIO)  │             │
│  │          │ │  coletas)│ │consumidor)│ │          │             │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘             │
└────────────────────────┬──────────────────────────────────────────┘
                         │ HTTP (proxy de perfil)
                         │ REST (API)
                         ▼
┌───────────────────────────────────────────────────────────────────┐
│              coleta-premiada-frontend/ (Next.js 16)                │
│   Server Components + Server Actions + Axios                      │
│                                                                   │
│   ┌─────────────┐  ┌─────────────┐  ┌────────────────────────┐   │
│   │  auth/      │  │ lib/        │  │ app/ (pages)           │   │
│   │  google-auth│  │ api-request │  │ ┌──────┐ ┌──────┐     │   │
│   │  login      │  │ api-auth    │  │ │(auth)│ │(dash)│     │   │
│   │  logout     │  │ api-collect │  │ └──────┘ └──────┘     │   │
│   └─────────────┘  └─────────────┘  └────────────────────────┘   │
│                                                                   │
│   CORE_API_URL=http://core:8000                                   │
│   COLLECTION_API_URL=http://coleta-ms:8001                        │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│              coleta-premiada-app/ (Expo / React Native)            │
│   SQLite local  │  SecureStore  │  Axios  │  Expo Router          │
│                                                                   │
│   API_BASE_URL=http://192.168.0.14:8002/api/ (aponta MS)          │
│   Autenticação via JWT do MS (coletores)                          │
│   Operação offline-first com sync automático                      │
└───────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────┐
│         coleta-premiada-observability/ (Prometheus + Grafana)      │
│   Rede: coleta-observability (external)                           │
│   Prometheus scrape: postgres-exporter:9187, mongodb-exporter:9216│
│   rabbitmq:15692, core:8000, ms-dev:8001, frontend (cAdvisor)     │
└───────────────────────────────────────────────────────────────────┘
```

---

## Contrato de Dados entre Serviços

### Fila `imoveis` (Core → MS)
```json
{
  "inscricao_imobiliaria": "string",
  "nome": "string",
  "cpf": "string",
  "endereco": "string",
  "acao": "adesao_programa|atualizacao_imovel",
  "latitude": null,
  "longitude": null,
  "elegivel": true,
  "ativo": true,
  "proprietario_id": 123,
  "num_moradores": 2,
  "iptu": "string",
  "numero": "string",
  "complemento": "string",
  "bairro": "string",
  "telefone": "string"
}
```

### Fila `coletas` (MS → Core)
```json
{
  "coleta_id": "uuid",
  "inscricao_imobiliaria": "string",
  "peso_total_kg": "string",
  "data_hora": "ISO-datetime"
}
```

---

## Limitações da Arquitetura Atual

1. **Acoplamento por segredo compartilhado:** MS valida JWT do Core usando `CORE_JWT_SECRET_KEY` — qualquer serviço com essa chave pode forjar tokens.
2. **Proxy HTTP síncrono:** Endpoints de supervisor no MS fazem chamada HTTP síncrona ao Core para validar perfil — ponto único de latência e falha.
3. **Sem API Gateway:** Frontend chama dois backends distintos com URLs diferentes — sem roteamento unificado, rate limiting ou autenticação centralizada.
4. **Consistência eventual sem saga:** Coletas criadas offline no MS são enviadas para o Core via fila — sem garantia de ordenação, sem rollback em caso de falha.
5. **Sem service discovery:** URLs de serviços são configuradas via variáveis de ambiente (DNS do Docker Compose resolve, mas sem failover dinâmico).
