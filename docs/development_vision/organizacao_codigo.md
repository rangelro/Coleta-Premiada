# Organização do Código

## coleta-premiada/ (Core Django)

### Estrutura de Pastas

```
core/
├── config/                          # Configuração do projeto Django
│   ├── settings.py                  # Config centralizada (DB, JWT, Celery, Prometheus)
│   ├── urls.py                      # Roteamento raiz (/api/*, /admin/, /metrics)
│   ├── wsgi.py / asgi.py            # Entry points WSGI/ASGI
│   ├── celery.py                    # App Celery + autodiscovery de tasks
│   └── pagination.py                # Classe de paginação padrão
│
├── accounts/                        # App: Usuários, roles, cidades, autenticação
│   ├── models.py                    # Usuario (AbstractBaseUser), Role, Cidade
│   ├── views.py                     # Auth, CRUD de usuários, Google OAuth
│   ├── serializers.py               # Validação de cadastro, perfis
│   ├── permissions.py               # IsGestor, IsMorador, IsSupervisor, etc.
│   ├── scoping.py                   # Escopo por cidade (gestor/supervisor)
│   └── urls.py
│
├── program/                         # App: Domínio do programa de reciclagem
│   ├── models.py                    # Programa, RegraPrograma, Imovel, SaldoPontos, Consolidacao, ConstantePontuacao
│   ├── views.py                     # CRUD de imóveis, programas, consolidação, relatórios
│   ├── serializers.py               # Validação de regras de negócio
│   ├── business_rules.py            # Regras de desconto (teto de 40%)
│   ├── signals.py                   # Post-save: publica RabbitMQ + agenda Celery
│   ├── tasks.py                     # Tarefas Celery (geocoding)
│   └── management/commands/         # Comandos administrativos
│       ├── geocodificar_imoveis.py  # Geocoding em lote
│       ├── passo_admin.py           # Seed de dados de teste
│       └── test_llm_report.py       # Teste manual LLM
│
├── collection/                      # App: Registros de coleta sincronizados do MS
│   ├── models.py                    # RegistroColeta, Evidencia, Contestacao
│   ├── views.py                     # CRUD + dispute analysis
│   ├── serializers.py
│   └── management/commands/
│       └── consume_queue.py         # Consumer RabbitMQ (fila 'coletas')
│
├── messaging/                       # Módulo de mensageria (cross-app)
│   ├── connection.py                # Factory de conexão pika
│   ├── producer.py                  # publish_message() genérico
│   └── consumer.py                  # Base de consumo
│
├── custom_audit/                    # App: Auditoria completa
│   ├── models.py                    # AuditLog (operacao, tabela, dados_antes/depois, ip)
│   ├── middleware.py                # Auditoria de SELECT (via request_store)
│   ├── signals.py                   # Auditoria de INSERT/UPDATE/DELETE (pre/post save)
│   ├── request_store.py             # Contexto thread-safe (contextvars)
│   └── views.py                     # Listagem e exportação CSV
│
├── reports/                         # App: Relatórios narrativos via LLM
│   ├── models.py                    # RelatorioLLM
│   ├── views.py                     # Geração e histórico
│   ├── llm_service.py              # Integração DeepSeek API
│   ├── local_llm_service.py        # Fallback LM Studio local
│   └── tests.py                     # Único app com testes reais (365 linhas)
│
├── Dockerfile                       # Multi-stage (base/dev/prod)
└── requirements.txt                 # Django 6.0.4, DRF 3.17.1, Celery, pika, geopy
```

### Padrão Arquitetural: Django Modular (Monólito Estruturado)

- **View Layer:** DRF Class-Based Views (generics.* + APIView) — sem ViewSets
- **Serializer Layer:** DRF Serializers com validação field-level e object-level
- **Model Layer:** Django ORM com modelos por app, sem soft-delete generalizado
- **Business Rules:** Extraídas para módulo separado (`business_rules.py`)
- **Event Publishing:** Signals Django disparam publicação RabbitMQ + tarefas Celery
- **Separação clara:** Cada app encapsula um domínio de negócio

### Convenções de Nomenclatura

- **Apps:** snake_case (accounts, program, custom_audit)
- **Models:** PascalCase (RegistroColeta, SaldoPontos, ConstantePontuacao)
- **Views:** PascalCase com sufixo View (ColetaCreateView, DisputeListView)
- **Serializers:** PascalCase com sufixo Serializer (ImovelSerializer, ColetaInputSerializer)
- **Permissões:** PascalCase prefixado com Is (IsGestor, IsOwnerOrGestor)
- **URLs:** kebab-case (/api/program/consolidations/run)

---

## coleta-premiada-micro/ (Collection MS Django)

### Estrutura de Pastas

```
config/
├── settings.py                   # MongoDB via django-mongodb-backend
├── urls.py                       # /, /admin/, /api/
├── apps.py                       # MongoAdminConfig, MongoAuthConfig, MongoContentTypesConfig
└── wsgi.py / asgi.py

coletores/                         # App: Agentes de coleta
├── models.py                     # Coletor (AbstractUser) com campos: matricula, zona, cargo
├── views.py                      # Register, Login, Logout, Me
├── serializers.py
└── urls.py

coleta/                            # App: Imóveis, coletas, geolocalização
├── models.py                     # Imovel (GeoJSON location + 2dsphere), Coleta (offline_id, status, sincronizado_core)
├── views.py                      # Imovel buscar/proximos/detail, Coleta CRUD/historico/pendentes, Supervisor views, Sincronizar
├── serializers.py                # ColetaInputSerializer (explícito), ColetaOutputSerializer, ImovelBuscarSerializer
├── managers.py                   # ImovelManager.upsert_from_evento(), ColetaManager.criar_idempotente()
├── urls.py
├── services/                     # Camada de serviços (cross-cutting)
│   ├── fila.py                   # Producer RabbitMQ (publicar_coleta)
│   ├── consumidor.py             # Consumer RabbitMQ (iniciar_consumidor)
│   └── storage.py                # MinIO upload
├── management/commands/
│   ├── consumir_imoveis.py       # Consumer loop infinito com auto-reconnect
│   └── reenviar_coletas.py       # Retry de sincronização

mongo_migrations/                  # Migrações customizadas para apps Django no MongoDB
├── admin/0001_initial.py
├── auth/0001_initial.py
└── contenttypes/0001_initial.py
```

### Padrão Arquitetural: Django com Camada de Serviços

- **View Layer:** APIView puro — sem generics, sem ViewSets
- **Manager Pattern:** Lógica de banco encapsulada em managers (`ImovelManager`, `ColetaManager`)
- **Service Layer:** Integrações externas isoladas em `services/` (fila, storage, consumidor)
- **Idempotência:** `ColetaManager.criar_idempotente()` por `offline_id`
- **Geolocalização:** Campo JSON `location` com índice 2dsphere + queries raw PyMongo para `$near`

### Diferenças do Core

| Característica | Core | Collection MS |
|---|---|---|
| View pattern | generics.* (DRF) | APIView puro |
| Banco | PostgreSQL 16 | MongoDB 7 |
| ORM | Django ORM relacional | django-mongodb-backend |
| Managers | Modelo padrão | Custom Managers explícitos |
| Serviços | Inline nas views | Extraídos para services/ |
| Testes | Stubs (vazios) + reports | Stub vazio + test_integration.py externo |

---

## coleta-premiada-frontend/ (Next.js 16)

### Estrutura de Pastas

```
app/
├── (auth)/                        # Route group: páginas públicas
│   ├── login/page.tsx
│   └── register/page.tsx
├── (dashboard)/                    # Route group: área logada
│   ├── (morador)/                  # Rotas do perfil morador
│   │   ├── layout.tsx              # Guard: valida perfil === 'morador'
│   │   └── coletas/ | imovel/ | morador/
│   ├── (gestor)/                   # Rotas do perfil gestor
│   │   ├── layout.tsx              # Guard: valida perfil gestor/gerente_geral
│   │   └── dashboard/ | usuarios/ | programas/ | auditoria/ | contestacoes/ | consolidacao/
│   ├── (supervisor)/               # Rotas do perfil supervisor
│   │   ├── layout.tsx
│   │   └── coletas/ | supervisor/
│   ├── (gerente_geral)/            # Rotas do perfil gerente_geral
│   │   ├── layout.tsx
│   │   └── cidades/
│   ├── coletas/page.tsx            # Dispatcher: renderiza view por role
│   ├── imoveis/
│   └── perfil/

actions/                            # Server Actions ("use server")
├── auth/                           # login-action, logout-action, google-auth-action, register-action
├── cidade/                         # CRUD de cidades
├── coleta/                         # buscar-coletas, buscar-evidencias, editar-coleta
├── contestacao/                    # morador-contestacao, gestor-contestacao
├── gestor/                         # CRUD de usuários e roles (gestor)
├── imovel/                         # CRUD de imóveis
├── program/                        # CRUD de programas, regras, constante
└── user/                           # buscar-moradores, update-user, manager-update-user

lib/                                # API clients e utilitários
├── api-request.ts                  # Base Axios → CORE_API_URL
├── api-authenticated-request.ts    # Autenticado (JWT de cookies) → Core
├── api-collection-authenticated-request.ts  # Autenticado → COLLECTION_API_URL
├── auth/                           # get-current-user.ts, manage-login.ts (cookies)
├── utils.ts                        # cn() helper (clsx + tailwind-merge)

types/                              # Tipos TypeScript
├── entities/                       # usuario.ts, imovel.ts, programa.ts, etc.
└── api/                            # paginated-response.ts

schemas/                            # Zod validation
├── auth/login-schema.ts
├── user/create-user-schema.ts
├── programs/create-program-schema.ts
└── ...

components/                         # Componentes React
├── ui/                             # shadcn/ui primitives (button, dialog, input, card, etc.)
├── Header/ | Sidebar/ | Footer/   # Layout
├── LoginForm/ | RegisterForm/     # Formulários
└── HomePage/                       # Landing page
```

### Padrão Arquitetural: Server Components + Server Actions

- **Renderização:** Server Components (fetch + render no servidor); Client Components apenas para interatividade
- **Mutações:** Server Actions ("use server") — sem API routes intermediárias
- **Validação:** Zod schemas validam no servidor antes de chamar APIs
- **Autenticação:** httpOnly cookies + Middleware (proxy.ts) com refresh automático
- **Controle de Acesso:** Layouts por grupo de rota validam `user.perfil` e redirecionam se não autorizado
- **Estado Global:** Nenhum — sidebar usa Context, demais dados via Server Components ou query params

---

## coleta-premiada-app/ (React Native / Expo)

### Estrutura de Pastas

```
app/                                # Expo Router (file-based)
├── _layout.tsx                     # Root: ServicesProvider → AuthProvider → AuthGuard → Stack
├── login.tsx
├── (tabs)/                         # Bottom tab navigator
│   ├── _layout.tsx                 # 4 tabs: Home, Coletar, Histórico, Perfil
│   ├── index.tsx                   # Dashboard do coletor
│   ├── coletar.tsx                 # Mapa + imóveis próximos
│   ├── historico.tsx
│   └── perfil.tsx
├── coletar/                        # Wizard 4 etapas
│   ├── identificar.tsx             # Etapa 1: identificar imóvel
│   ├── pesar.tsx                   # Etapa 2: pesar material
│   ├── foto.tsx                    # Etapa 3: foto opcional
│   ├── confirmar.tsx               # Etapa 4: confirmar + salvar
│   └── sucesso.tsx
├── historico/detalhe.tsx
├── mapas/                          # Mapas offline (download + listagem)
└── sincronizacao.tsx

services/                           # Solicitam à API + fallback offline
├── api.ts                          # Axios instance + interceptors (401, offline-save)
├── ApiClient.ts                    # apiClient (auth) + apiClientOpen
├── AuthService.ts                  # login, logout, me
├── ColetaService.ts                # criar, historico, sync
├── ImovelService.ts                # proximos, buscar, detalhe
└── database/                       # SQLite local
    ├── db.ts                       # initDatabase(), getDatabase()
    ├── ColetaRepository.ts         # CRUD offline de coletas
    ├── ImovelRepository.ts         # Cache + consulta espacial (Haversine)
    └── MapaRepository.ts           # Armazenamento de mapas offline

hooks/                              # Custom hooks de dados
├── useAutoSync.ts                  # Sync automático em background
├── useHistorico.ts                 # Histórico paginado (online/offline)
├── useHomeDashboard.ts             # Dados da home
├── useOfflineStatus.ts             # Contagem de pendentes + conectividade
└── useSincronizacao.ts             # Tela de sync

context/
├── AuthContext.tsx                  # Estado de autenticação + SecureStore
└── ServicesContext.tsx              # DI de serviços

components/ui/                      # Design system próprio
├── Btn.tsx                         # Botão (default/primary/ghost/danger)
├── Card.tsx                        # Card (default/soft/accent)
├── Steps.tsx                       # Stepper de progresso
├── AppBar.tsx                      # Barra superior
└── icon-symbol.tsx                 # Ícones (MaterialIcons / SF Symbols)

store/FotoStore.ts                  # Singleton de foto em memória (entre telas)
```

### Padrão Arquitetural: Offline-First com Repository Pattern

- **Offline-first:** Dados salvos primeiro no SQLite local antes de tentar API
- **Repository Pattern:** `ColetaRepository`, `ImovelRepository` encapsulam operações SQLite
- **Service Layer:** Services chamam API → fallback para repositório local
- **Auto-Sync:** Hook `useAutoSync()` tenta reenviar coletas pendentes em background
- **Idempotência:** `offline_id` UUID gerado no dispositivo previne duplicatas
- **Interceptor de Rede:** Axios interceptor captura 401 (limpa sessão) e network errors (salva offline e lança `OfflineSavedError`)
