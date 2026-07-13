# Padrões e Convenções

## Tratamento de Erros

### Core (Django REST Framework)

**Validação em Serializers:**
- `serializers.ValidationError` para erros field-level e object-level
- DRF converte automaticamente em resposta 400 com `{ "field": ["message"] }`
- Validações de negócio em métodos `validate_<field>()` e `validate()`

**Erros em Views:**
- DRF `PermissionDenied` → 403 (classes de permissão)
- DRF `NotAuthenticated` → 401 (SimpleJWT)
- DRF `Http404` → 404 (`get_object_or_404`)
- Exceções genéricas capturadas com try/except → 500 + log

**Erros em Consumer RabbitMQ:**
```python
try:
    processar_mensagem(payload)
    ch.basic_ack(delivery_tag=method.delivery_tag)
except json.JSONDecodeError:
    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)  # descarta
except Exception:
    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)  # evita loop infinito
```

**Erros em Celery Tasks:**
```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def geocodificar_imovel(self, imovel_id):
    try:
        # ...
    except (GeocoderTimedOut, GeocoderServiceError) as exc:
        raise self.retry(exc=exc)
```

### Collection MS

**Validação manual nas views (sem DRF generics):**
```python
try:
    validate_password(senha)
except ValidationError as exc:
    return Response({'error': exc.messages}, status=400)
```

**Padrão de retorno para erros:**
- `400` — validação de dados
- `401` — autenticação
- `403` — permissão negada
- `404` — recurso não encontrado
- `502` — falha em integração externa (MinIO)
- `207 Multi-Status` — sincronização batch parcialmente falha

### Frontend (Next.js)

**Server Actions:**
```typescript
// Padrão de retorno: { success: true, data: T } | { success: false, errors: string[] }
if (!parsedFormData.success) {
  return { ...state, errors: getZodErrorMessages(parsedFormData.error), ... };
}
```

**API Client:**
```typescript
// api-request.ts extrai erros de AxiosError (formato string, message, ou object DRF)
catch (err: any) {
  const messages = extrairErros(err);
  return { success: false, errors: messages, status };
}
```

### Mobile

**Interceptor Axios com tratamento offline:**
```typescript
// Network error + POST /coletas → salva em SQLite, lança OfflineSavedError
// 401 → limpa sessão, redireciona para login
// Outros erros → lança Error(data?.error ?? `Erro ${status}`)
```

---

## Validação de Dados

### Core (Django)

| Camada | Mecanismo | Exemplo |
|---|---|---|
| Model | `model.clean()` | `clean()` em Usuario valida cidade obrigatória por perfil |
| Serializer (field) | `validate_<field>()` | `validate_titular()` verifica perfil 'morador' |
| Serializer (object) | `validate()` | `validate()` em Programa verifica data_fim > data_inicio |
| View | `query_params` manual | `data_inicio` validado como ISO date |
| Password | Validadores Django | `MinimumLengthValidator`, `CommonPasswordValidator` |

### Collection MS

| Camada | Mecanismo | Exemplo |
|---|---|---|
| Serializer explícito | `ColetaInputSerializer` com tipos explícitos | `DecimalField`, `UUIDField`, `DateTimeField` |
| View manual | `try/except` com `ValidationError` | Senha, tipos de query params |
| Idempotência | `offline_id` unique | `ColetaManager.criar_idempotente()` |

### Frontend (Next.js)

| Camada | Mecanismo | Exemplo |
|---|---|---|
| Servidor (Action) | Zod schema `.safeParse()` | `LoginSchema`, `CreateProgramSchema` |
| Servidor (fetch) | Tipos TypeScript + validação manual | Schemas de entidades em `types/entities/` |
| Cliente | Tipos TypeScript + React Hook Form | Formulários com validação Zod no submit |

### Mobile

| Camada | Mecanismo |
|---|---|
| API | Validação pelo servidor (MS retorna erros) |
| Local | Typescript strict + validação manual em services |
| Idempotência | UUID offline_id gerado no dispositivo |

---

## Padronização de APIs

### URL Patterns

```
/api/{dominio}/{recurso}[/{id}][/{subrecurso}]
```

- Core: `/api/accounts/*`, `/api/program/*`, `/api/collection/*`, `/api/audit/*`, `/api/reports/*`
- MS: `/api/auth/*`, `/api/imoveis/*`, `/api/coletas/*`, `/api/supervisor/*`

### Padrões de Resposta

**Listas paginadas (Core):**
```json
{
  "count": 100,
  "next": "http://.../?page=2",
  "previous": null,
  "results": [ ... ]
}
```

**Criação bem-sucedida:** HTTP 201 + objeto completo
**Atualização bem-sucedida:** HTTP 200 + objeto completo
**Exclusão:** HTTP 204 sem corpo
**Erro de validação:** HTTP 400 + `{ "campo": ["mensagem"] }`

### Cabeçalhos de Autenticação

- `Authorization: Bearer <jwt>` em todas as requisições autenticadas
- Token de refresh via `POST /api/token/refresh/` com corpo `{ "refresh": "..." }`

---

## Convenções de Nomenclatura

### Backend (Python/Django)

| Item | Convenção | Exemplo |
|---|---|---|
| Apps | `snake_case` | `custom_audit`, `accounts` |
| Models | `PascalCase` | `RegistroColeta`, `SaldoPontos`, `ConstantePontuacao` |
| Views | `PascalCase + View` | `ColetaCreateView`, `GoogleOAuthLoginView` |
| Serializers | `PascalCase + Serializer` | `ColetaInputSerializer`, `ImovelSerializer` |
| Permissions | `PascalCase + Is` | `IsGestor`, `IsOwnerOrGestor` |
| Managers | `PascalCase + Manager` | `ImovelManager`, `ColetaManager` |
| Services | `PascalCase + Service` | `LLMReportService`, `LocalLLMReportService` |
| URLs | `kebab-case` | `/api/program/consolidations/run` |
| Variáveis | `snake_case` | `desconto_maximo`, `peso_total_kg` |
| Constantes | `UPPER_SNAKE_CASE` | `DESCONTO_MAXIMO`, `PERFIS_ESCOPADOS_POR_CIDADE` |

### Frontend (TypeScript/Next.js)

| Item | Convenção | Exemplo |
|---|---|---|
| Arquivos | `kebab-case` | `login-action.ts`, `get-current-user.ts` |
| Componentes | `PascalCase` | `DashboardShell`, `CreateProgramForm` |
| Funções | `camelCase` | `getCurrentUser`, `setTokens` |
| Tipos/Interfaces | `PascalCase` | `PaginatedResponse<T>`, `Usuario` |
| Actions | `camelCase + Action` | `loginAction`, `googleAuthAction` |
| Diretórios app | `kebab-case` | `(gestor)/`, `(morador)/` |

### Mobile (TypeScript/Expo)

| Item | Convenção | Exemplo |
|---|---|---|
| Arquivos | `kebab-case` | `useAutoSync.ts`, `ColetaRepository.ts` |
| Componentes | `PascalCase` | `AuthGuard`, `Btn`, `Steps` |
| Hooks | `camelCase + use` | `useAutoSync`, `useOfflineStatus` |
| Services | `PascalCase + Service` | `AuthService`, `ColetaService` |
| Repositories | `PascalCase + Repository` | `ColetaRepository`, `ImovelRepository` |

---

## Auditoria (Core)

Sistema de auditoria completo implementado via:
- **Signals Django** (`pre_save`, `post_save`, `post_delete`): capturam INSERT/UPDATE/DELETE com snapshots de `dados_antes` e `dados_depois` em JSON
- **Middleware**: captura operações SELECT (registra toda consulta à lista de entidades)
- **Contexto thread-safe**: `request_store.py` com `contextvars` para capturar usuário e IP em signals sem request
- **Dados registrados:** timestamp, usuário, operação, tabela, objeto_id, dados_antes/depois, IP, endpoint
- **Exportação:** CSV para auditoria externa
- **Admin read-only:** Modelo AuditLog registrado no Django Admin como somente leitura

---

## Versionamento e Migrações

### Core
- Migrações Django padrão (`python manage.py makemigrations / migrate`)
- CI verifica migrações consistentes via `makemigrations --check --dry-run`

### Collection MS
- Migrações Django com backend MongoDB
- Migrações customizadas para `admin`, `auth`, `contenttypes` em `mongo_migrations/`
- Migrações de dados manuais (ex: `0007` para criar índices 2dsphere)

### Frontend
- Sem migrações (aplicação stateless, dados via API)

### Mobile
- Schema SQLite versionado via `initDatabase()` no bootstrap do app
- Sem migrations — schema é recriado se alterado

---

## Testes

| Projeto | Cobertura | Frameworks |
|---|---|---|
| Core | Stubs vazios em accounts/collection/program | `unittest.TestCase` (Django) |
| Core | Reports com 22 testes (LLMService + Views) | `unittest.mock` (patch) |
| MS | Stub vazio | Django TestCase |
| MS | Teste de integração externo (653 linhas) | Script Python sequencial |

**Ausência generalizada de testes:** Apenas 1 dos 4 apps backend tem testes reais. Frontend e Mobile não possuem infraestrutura de teste.
