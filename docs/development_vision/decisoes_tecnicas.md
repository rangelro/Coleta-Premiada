# Decisões Técnicas

## Escolha de Tecnologias

### Django 6.0 + DRF 3.17 (Core e MS)

| Decisão | Justificativa | Trade-off |
|---|---|---|
| Django 6.0 (bleeding edge) | Acesso a recursos mais recentes do framework (ex: suporte nativo a MongoDB) | Ecossistema menos maduro, documentação limitada, risco de breaking changes |
| DRF Class-Based Views | Reuso via herança, menos código boilerplate que function views | Menos flexibilidade que APIView puro para casos complexos |
| DRF sem ViewSets (MS) | Controle explícito de cada endpoint | Mais código repetitivo, sem roteamento automático |
| django-mongodb-backend (MS) | ORM Django unificado mesmo com MongoDB heterogêneo | Perda de recursos relacionais (joins, constraints), camada de abstração vazando |

### Django vs. FastAPI

O Core e MS usam Django/DRF em vez de FastAPI. Implicações:
- **Síncrono por padrão:** Gunicorn com workers síncronos para I/O-bound. FastAPI teria performance assíncrona nativa.
- **Baterias incluídas:** ORM, admin, migrations, signals — ecossistema completo sem composição adicional.
- **DRF serializers:** Mais verbosos que Pydantic, mas integram-se nativamente ao ORM Django.

### Next.js 16 (App Router) — Frontend

| Decisão | Justificativa | Trade-off |
|---|---|---|
| App Router (Server Components) | SSR com zero JS no cliente para páginas estáticas, SEO melhor, menor bundle | Curva de aprendizado, mixed-mode Client/Server complexo |
| Server Actions | Mutação sem criar API routes intermediárias — menos código | Acoplamento à infraestrutura Next.js, difícil de testar isoladamente |
| shadcn/ui + Tailwind 4 | Componentes acessíveis e customizáveis sem dependência pesada | Tailwind 4 ainda instável (breaking changes do CSS-in-JS antecessor) |
| Sem estado global (Redux/Zustand) | Server Components + URL params substituem estado global | Complexidade maior para estados compartilhados entre rotas irmãs |

### React Native + Expo SDK 54 — Mobile

| Decisão | Justificativa | Trade-off |
|---|---|---|
| Expo (managed workflow) | Build simplificado, sem configuração nativa, OTA updates | Limitações em módulos nativos customizados |
| Expo Router (file-based) | Consistência com Next.js no frontend web | Framework novo, menos exemplos |
| expo-sqlite | Armazenamento local leve sem depender de Realm ou WatermelonDB | Sem sistema de migrations, schema gerenciado manualmente |
| Offline-first com Axios interceptor | Transparente para o desenvolvedor, sem overhead de bibliotecas complexas | Lógica de conflito inexistente (último vence) |

### PostgreSQL 16 (Core) + MongoDB 7 (MS)

| Decisão | Justificativa | Trade-off |
|---|---|---|
| PostgreSQL no Core | Dados relacionais complexos (usuários ↔ roles ↔ imóveis ↔ programas ↔ pontuação) com joins e constraints | — |
| MongoDB no MS | Esquema flexível para dados geoespaciais, sem necessidade de joins complexos | Duas tecnologias de banco para manter, sem transações distribuídas |
| django-mongodb-backend | Unifica ORM entre os dois backends Django | Camada fina que vaza abstração; algumas features do Django ORM não funcionam |

### RabbitMQ (Mensageria)

| Decisão | Justificativa | Trade-off |
|---|---|---|
| RabbitMQ sobre Redis Pub/Sub | Garantia de entrega, filas duráveis, dead-letter, ACK/NACK | Mais pesado que Redis, requer configuração adicional |
| pika (sem Celery para consumo) | Consumo de filas em management command separado | Sem retry agendado, sem dead-letter com TTL, sem monitoria de filas mortas |
| Duas filas ponto-a-ponto (sem exchange) | Simplicidade máxima para dois produtores/consumidores | Sem roteamento baseado em routing keys, sem fanout/topics |

### MinIO (Object Storage)

| Decisão | Justificativa |
|---|---|
| MinIO sobre AWS S3 | Simplicidade local, API compatível com S3, sem dependência cloud |
| Sem CDN | Fotos servidas diretamente pelo MinIO, sem cache geográfico |

---

## Trade-offs Implícitos

### Consistência Eventual sem Saga

Coletas criadas offline no MS são enviadas para o Core via fila RabbitMQ:
- **Problema:** Se o Core falhar ao processar (ex: imóvel não encontrado, programa inativo), a mensagem é descartada (nack sem requeue) e a coleta nunca chega ao Core.
- **Impacto:** Morador não recebe pontuação, mas no MS a coleta aparece como criada.
- **Mitigação:** Campo `sincronizado_core: false` + comando `reenviar_coletas` para retry manual.

### Autenticação Dupla no MS

- O MS mantém seu próprio sistema de usuários (coletores) + valida JWT do Core manualmente.
- **Risco:** A chave `CORE_JWT_SECRET_KEY` é compartilhada entre Core e MS — comprometimento de um serviço compromete o outro.
- **Mitigação:** Nenhuma — segredo compartilhado hardcoded em configuração.

### Sem API Gateway

- Frontend web chama dois backends com URLs diferentes (CORE_API_URL e COLLECTION_API_URL).
- **Problema:** Sem rate limiting centralizado, sem autenticação unificada, sem roteamento por path prefix.
- **Impacto:** Cada backend precisa implementar CORS, autenticação e rate limiting separadamente.

### Sem Service Discovery

- URLs são resolvidas via DNS do Docker Compose (nomes de serviço).
- **Problema:** Mudança de infraestrutura (Kubernetes, swarm, IPs estáticos) exige reconfiguração manual de variáveis de ambiente.

### Sem Distributed Tracing

- Não há Jaeger, OpenTelemetry ou Zipkin.
- **Impacto:** Rastrear uma requisição do mobile → MS → RabbitMQ → Core requer correlação manual de logs.

### Portas Conflitantes

- MS usa portas não-padrão (MongoDB 27019, RabbitMQ 5673/15673) para coexistir com o stack Core.
- **Problema:** Configuração mental adicional, scripts de desenvolvimento precisam saber dois conjuntos de portas.

---

## Possíveis Limitações ou Riscos Técnicos

| Risco | Severidade | Descrição | Mitigação |
|---|---|---|---|
| **Perda de mensagens RabbitMQ** | Alta | Consumer descarta mensagens com erro de processamento sem dead-letter | Comando `reenviar_coletas`; considerar DLQ futura |
| **Token JWT compartilhado** | Alta | MS valida JWT do Core com mesma chave secreta | Adotar microsserviço de autenticação ou troca de chaves assimétrica |
| **Django-mongodb-backend imaturo** | Média | Backend MongoDB para Django 6.0 pode ter bugs ou limitações não documentadas | Testes de integração frequentes; fallback para PyMongo raw |
| **Sem testes (frontend + mobile)** | Alta | Qualquer refatoração pode quebrar funcionalidades sem detecção | Adicionar testes críticos antes de refatorações |
| **MongoDB sem transactions** | Média | Sem atomicidade multi-documento (MongoDB < 4.0 replica set) | Operações idempotentes com offline_id |
| **DeepSeek API como dependência crítica** | Média | Relatórios LLM falham se API estiver fora | Fallback LM Studio local |
| **Geocoding com rate limit** | Baixa | Nominatim permite 1 req/s — lotes grandes demoram | Celery com `default_retry_delay=60` |
| **Mobile sem env vars** | Média | API URL hardcoded — diferente para cada desenvolvedor | Adotar `expo-constants` + .env |
| **Sem migrations versionadas (mobile)** | Baixa | Alteração de schema SQLite requer delete manual do banco | Adicionar sistema de migrações (ex: `migration number` na tabela `_meta`) |

---

## Decisões de Arquitetura por Camada

### Organização de Código

| Decisão | Justificativa |
|---|---|
| Monólito modular no Core (apps Django) vs. microserviços granulares | Coesão do domínio de programa de reciclagem justifica monólito; apenas coleta de campo foi extraída para MS |
| Signals Django para eventos | Desacoplamento entre modelos e efeitos colaterais (RabbitMQ, Celery) |
| Managers customizados no MS | `ImovelManager.upsert_from_evento()` e `ColetaManager.criar_idempotente()` encapsulam lógica de sincronização e idempotência |
| APIView puro no MS (sem generics) | Controle explícito de cada endpoint — adequado para microsserviço com endpoints específicos |
| Server Components + Server Actions | Máximo de processamento no servidor, mínimo JS no cliente |

### Auditoria

| Decisão | Justificativa |
|---|---|
| Signals + Middleware | Audit trail completo sem poluir as views |
| contextvars para request context | Signals não têm acesso ao request — contextvars resolvem isso thread-safe |
| SELECT auditado via middleware | Operações de leitura são as mais frequentes; auditar via middleware é não-intrusivo |

### LLM Reports

| Decisão | Justificativa |
|---|---|
| Dual-mode (cloud + local) | Resiliência: se DeepSeek cair, LM Studio local assume |
| OpenAI-compatible SDK | Mesmo cliente para DeepSeek e LM Studio — zero mudança de código |
| Agregação SQL antes do prompt | Reduz tokens e custo; envia apenas dados agregados para o LLM |

### Infraestrutura

| Decisão | Justificativa |
|---|---|
| Docker Compose (não Kubernetes) | Simplicidade para desenvolvimento local e deploy single-host |
| Rede external compartilhada | Descoberta de serviços cross-repositório sem service mesh |
| Multi-stage Dockerfiles | Imagens de produção mínimas (especialmente Next.js standalone) |
| db-backup com cron + pg_dump | Backup sem depender de serviços externos ou cloud |

---

## Padrões Não Adotados (e por quê)

| Padrão | Não adotado porque... |
|---|---|
| **API Gateway** | Complexidade desnecessária para 2 backends; reavaliar se novos serviços surgirem |
| **GraphQL** | API REST simples o suficiente para os domínios atuais |
| **WebSockets** | Atualizações em tempo real não são necessárias (consistência eventual é aceitável) |
| **Kubernetes** | Sistema single-host; Docker Compose atende |
| **Centralized Error Tracking (Sentry)** | Não implementado — erros capturados via logs Docker |
| **CQRS / Event Sourcing** | Complexidade excessiva para o domínio; consistência imediata é suficiente para a maioria das operações |
| **Hexagonal Architecture** | Django não favorece isolamento de infraestrutura; padrão modular atual é pragmático |
