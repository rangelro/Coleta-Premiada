# Mapeamento de API — Coleta Premiada

> Gerado em 2026-06-29. Cobre os três projetos: `Coleta-Premiada` (Core API, porta 8001), `cp-collection-ms` (MS de Coleta, porta 8002) e `coleta-premiada-frontend` (Next.js, porta 3001).

---

## Arquitetura Geral

```
┌─────────────────────────────────────────────────────────────┐
│                    coleta-premiada-frontend                  │
│                     Next.js (porta 3001)                     │
│                                                             │
│  Server Actions / lib → CORE_API_URL (porta 8001)           │
│  COLLECTION_API_URL (porta 8002) → NÃO UTILIZADO           │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP + Bearer JWT
                               ▼
┌──────────────────────────────────────────────────────────────┐
│               Coleta-Premiada — Core API (porta 8001)        │
│                  Django 6 + DRF + PostgreSQL                 │
│                  Auth: JWT (SimpleJWT), Google OAuth2        │
│                  Celery (geocoding), Prometheus              │
└──────────┬──────────────────────────────┬────────────────────┘
           │ RabbitMQ: publica `imoveis`  │ RabbitMQ: consome `coletas`
           ▼                              ▲
┌──────────────────────────────────────────────────────────────┐
│             cp-collection-ms — MS de Coleta (porta 8002)     │
│                  Django 6 + DRF + MongoDB + MinIO            │
│                  Auth: JWT próprio (matricula/senha)         │
│                  RabbitMQ: consome `imoveis`, publica `coletas`│
└──────────────────────────────────────────────────────────────┘
```

### Perfis de usuário (Core)

| Perfil | Descrição |
|---|---|
| `gestor` | Administrador — acesso total de escrita |
| `supervisor` | Leitor privilegiado — pode editar constante de pontuação |
| `morador` | Cidadão — vê apenas seus próprios dados |

---

## 1. Endpoints Utilizados pelo Frontend

> **Base URL:** `CORE_API_URL` (env var; default `http://localhost:8001`).
> Todas as chamadas usam `lib/api-request.ts` (axios) ou `lib/api-authenticated-request.ts` (axios + Bearer token do cookie `accessToken`).

---

### 1.1 POST `/api/token/` — Login

**Auth:** Nenhuma  
**Arquivo:** `actions/auth/login-action.ts`

**Request body:**
```json
{
  "email": "string",
  "password": "string"
}
```

**Response 200:**
```json
{
  "access": "string (JWT)",
  "refresh": "string (JWT)"
}
```

**Comportamento:** Os tokens são salvos em cookies httpOnly (`accessToken`, `refreshToken`). Redireciona para `/` após sucesso.

---

### 1.2 POST `/api/accounts/auth` — Registro de usuário

**Auth:** Nenhuma  
**Arquivo:** `actions/auth/register-action.ts`

**Request body:**
```json
{
  "nome": "string",
  "email": "string",
  "perfil": "supervisor | morador | gestor",
  "password": "string"
}
```

**Response 201:** Objeto `User` completo (não consumido pelo frontend, apenas verifica `success`).

**Comportamento:** Redireciona para `/login` após sucesso.

---

### 1.3 POST `/api/accounts/auth/logout` — Logout

**Auth:** Bearer token  
**Arquivo:** `actions/auth/logout-action.ts`

**Request body:** Nenhum  
**Response 204:** Sem conteúdo

**Comportamento:** Limpa os cookies independente do retorno da API. Redireciona para `/login`.

> ⚠️ **Bug conhecido:** O backend exige `{ "refresh": "string" }` no body para invalidar o token, mas o frontend não envia nada. O logout funciona localmente (cookies apagados) mas o refresh token não é invalidado no servidor.

---

### 1.4 GET `/api/accounts/auth/me` — Usuário logado

**Auth:** Bearer token  
**Arquivos:** `lib/auth/get-current-user.ts`, `proxy.ts`

**Request:** Sem body

**Response 200:**
```json
{
  "id": 1,
  "email": "string",
  "cpf": "string | null",
  "nome": "string",
  "perfil": "supervisor | morador | gestor",
  "ativo": true,
  "roles": [
    {
      "id": 1,
      "nome": "string",
      "descricao": "string | null",
      "ativo": true
    }
  ]
}
```

**Uso:** Chamado em todos os layouts de dashboard para autenticação e roteamento por perfil (`/gestor`, `/supervisor`, `/morador`).

---

### 1.5 POST `/api/token/refresh/` — Renovação de token

**Auth:** Nenhuma  
**Arquivo:** `proxy.ts` (⚠️ não está registrado como middleware)

**Request body:**
```json
{
  "refresh": "string"
}
```

**Response 200:**
```json
{
  "access": "string (JWT)",
  "refresh": "string (JWT)"
}
```

> ⚠️ **Bug crítico:** `proxy.ts` exporta `proxy()` e `config` (matcher), mas Next.js exige que o middleware esteja em `middleware.ts` na raiz do projeto. Esse arquivo não existe — portanto, a renovação automática de token **não funciona**. Usuários com token expirado são simplesmente bloqueados.

---

## 2. Endpoints Disponíveis no Core API (não chamados pelo frontend)

> Base: `http://localhost:8001/api`

### 2.1 Autenticação

| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| POST | `/accounts/auth/google` | Nenhuma | Login/cadastro via Google OAuth2 |
| PATCH | `/accounts/auth/me` | Bearer | Atualiza nome/CPF do próprio usuário |
| DELETE | `/accounts/auth/me` | Bearer | Soft-delete da própria conta |

#### POST `/accounts/auth/google`
```json
// Request
{ "code": "string", "redirect_uri": "string" }

// Response 200
{ "access": "string", "refresh": "string" }
```
Cria usuário com `perfil='morador'` se o e-mail não existir.

#### PATCH `/accounts/auth/me`
```json
// Request (parcial)
{ "nome": "string", "cpf": "string" }

// Response 200 — objeto User completo
```

---

### 2.2 Usuários (apenas `gestor`)

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/accounts/users` | Lista com filtros: `perfil`, `ativo`, `search` (nome/email), paginação |
| POST | `/accounts/users` | Cria qualquer perfil de usuário |
| GET | `/accounts/users/:pk` | Detalhe |
| PATCH | `/accounts/users/:pk` | Atualiza nome, CPF, perfil, ativo |
| DELETE | `/accounts/users/:pk` | Soft-delete (não pode deletar a própria conta) |
| POST | `/accounts/users/:id/roles/:roleId` | Atribui role ao usuário |

**Serializer Usuario:**
```json
{
  "id": 1,
  "email": "string",
  "cpf": "string | null",
  "nome": "string",
  "perfil": "supervisor | morador | gestor",
  "ativo": true,
  "roles": [{ "id": 1, "nome": "string", "descricao": "string", "ativo": true }]
}
```

---

### 2.3 Roles (apenas `gestor`)

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/accounts/roles` | Lista todas as roles |
| POST | `/accounts/roles` | Cria role: `{ nome, descricao, ativo }` |
| GET | `/accounts/roles/:pk` | Detalhe |
| PATCH | `/accounts/roles/:pk` | Atualiza parcialmente |

---

### 2.4 Portal do Cidadão (`/api/accounts/me/`)

Requer Bearer token do morador logado.

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/accounts/me/history` | Histórico de coletas do morador |
| GET | `/accounts/me/points` | Total de pontos acumulados |
| GET | `/accounts/me/benefits` | Saldos de desconto por ciclo |
| GET | `/accounts/me/program` | Programa ativo atual |

**GET `/accounts/me/history` — Response:**
```json
[
  {
    "id": 1,
    "id_microservico": "string",
    "imovel": 1,
    "pontuacao": "10.50",
    "data_hora_coleta": "2026-05-19T10:00:00Z",
    "peso_kg": "2.500"
  }
]
```

**GET `/accounts/me/points` — Response:**
```json
{ "pontos_acumulados": "125.50" }
```

**GET `/accounts/me/benefits` — Response:**
```json
[
  {
    "id": 1,
    "imovel": 1,
    "programa": 1,
    "ciclo": "05-2026",
    "desconto_percentual": "12.50",
    "atualizado": "2026-05-19T10:00:00Z"
  }
]
```

**GET `/accounts/me/program` — Response:**
```json
{
  "id": 1,
  "nome": "string",
  "data_inicio": "2026-01-01",
  "data_fim": "2026-12-31",
  "desconto_maximo": "40.00"
}
```

---

### 2.5 Imóveis (`/api/program/properties`)

| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| GET | `/program/properties` | Autenticado | Lista; morador vê apenas os seus. Filtros: `bairro`, `cidade`, `ativo`, `search` |
| POST | `/program/properties` | Autenticado | Cria imóvel (dispara geocoding e RabbitMQ) |
| GET | `/program/properties/:pk` | Autenticado | Detalhe |
| PATCH | `/program/properties/:pk` | Gestor/Supervisor | Atualização parcial |
| POST | `/program/properties/:id/users` | Gestor/Supervisor | Vincula morador ao imóvel: `{ "user_id": int }` |
| DELETE | `/program/properties/:id/users/:userId` | Gestor/Supervisor | Remove morador do imóvel (titular não pode ser removido) |

**Serializer Imovel:**
```json
{
  "id": 1,
  "inscricao": "string (único)",
  "titular": 1,
  "cep": "60000-000",
  "logradouro": "string",
  "numero": "string",
  "complemento": "string | null",
  "bairro": "string",
  "cidade": "string",
  "estado": "CE",
  "num_moradores": 3,
  "latitude": "-3.7172",
  "longitude": "-38.5433",
  "geocodificacao_falhou": false,
  "ativo": true,
  "data_adesao": "2026-01-15"
}
```

---

### 2.6 Programas (`/api/program/programs`)

| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| GET | `/program/programs` | Autenticado | Lista programas (escopado por cidade para gestor/supervisor) |
| POST | `/program/programs` | **Gestor** (não gerente_geral) | Cria programa; `cidade` obrigatória e deve ser a cidade do gestor |
| GET | `/program/programs/:pk` | Autenticado | Detalhe — gestor/supervisor recebem 404 para outra cidade |
| PATCH | `/program/programs/:pk` | **Gestor** (não gerente_geral) | Atualização parcial |
| GET | `/program/programs/:id/rules` | Autenticado | Regras do programa (escopado por cidade) |
| PATCH | `/program/programs/:id/rules` | **Gestor** (não gerente_geral) | Atualiza regras |

> **gerente_geral**: somente leitura nestes endpoints (escrita retorna 403).

**Serializer Programa:**
```json
{
  "id": 1,
  "nome": "string",
  "descricao": "string",
  "cidade": 1,
  "cidade_nome": "Pau dos Ferros",
  "data_inicio": "2026-01-01",
  "data_fim": "2026-12-31",
  "ativo": true,
  "desconto_maximo": "40.00",
  "regras": {
    "pontos_por_real": "10.00",
    "minimo_para_beneficio": 100,
    "permite_acumulo_ciclos": false
  }
}
```

---

### 2.7 Consolidações (`/api/program/consolidations`)

| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| POST | `/program/consolidations/run` | **Gestor** (não gerente_geral) | Executa consolidação; gestor só pode consolidar programas da própria cidade (404 para outra) |
| GET | `/program/consolidations` | Gestor/Supervisor/Gerente Geral | Lista — escopado por cidade para gestor/supervisor |
| GET | `/program/consolidations/:pk` | Gestor/Supervisor/Gerente Geral | Detalhe — escopado por cidade para gestor/supervisor |

**POST `/program/consolidations/run` — Request:**
```json
{ "programa_id": 1, "ciclo": "05-2026" }
```

**Response 201:**
```json
{
  "id": 1,
  "programa": 1,
  "executada_em": "2026-05-19T10:00:00Z",
  "executada_por": 1,
  "status": "concluida | falhou",
  "total_imoveis": 150,
  "total_pontos": "1875.00",
  "observacao": "string"
}
```

**Regras de negócio:** Imóveis abaixo de `minimo_para_beneficio` são ignorados. Desconto = `pontos / pontos_por_real`. Cap máximo: `40%` (hard-coded) e `Programa.desconto_maximo`.

---

### 2.8 Benefícios (`/api/program/benefits`)

| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| GET | `/program/benefits` | Gestor/Supervisor | Lista com filtros: `imovel_id`, `programa_id`, `ciclo` |
| GET | `/program/benefits/:propertyId/:programaId` | Autenticado | Benefícios de um imóvel em um programa, por ciclos |

**GET `/program/benefits/:propertyId/:programaId` — Response:**
```json
{
  "imovel": "inscricao_string",
  "titular": "nome_string",
  "programa": "nome_string",
  "desconto_total_percentual": "12.50",
  "saldos_por_ciclo": [
    {
      "id": 1,
      "imovel": 1,
      "programa": 1,
      "ciclo": "05-2026",
      "desconto_percentual": "12.50",
      "atualizado": "2026-05-19T10:00:00Z"
    }
  ]
}
```

---

### 2.9 Relatórios de Participação (`/api/program/reports`)

| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| GET | `/program/reports/participation` | Gestor/Supervisor | Coletas e pontos por imóvel |
| GET | `/program/reports/ranking` | Gestor/Supervisor | Ranking por pontos (decrescente) |
| GET | `/program/reports/impact` | Gestor/Supervisor | Totais gerais do programa |

**GET `/program/reports/impact` — Response:**
```json
{
  "total_coletas": 1250,
  "total_pontos": "18750.00",
  "total_imoveis_participantes": 200,
  "soma_desconto_percentual": "2400.00"
}
```

---

### 2.10 Constante de Pontuação (`/api/program/scoring-constant`)

| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| GET | `/program/scoring-constant` | Autenticado | Retorna a constante atual |
| PATCH | `/program/scoring-constant` | **Supervisor** | Atualiza `pontos_por_kg` |

**Response:**
```json
{
  "pontos_por_kg": "1.50",
  "atualizado_em": "2026-05-01T08:00:00Z",
  "atualizado_por": 3
}
```

---

### 2.11 Coletas — Core (`/api/collection/collections`)

| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| GET | `/collection/collections` | Autenticado | Lista; morador vê apenas as suas. Filtros: `imovel_id`, `programa_id`, `data_inicio`, `data_fim` |
| POST | `/collection/collections` | Gestor/Supervisor | Registro manual (normalmente via RabbitMQ) |
| GET | `/collection/collections/:pk` | Autenticado | Detalhe |
| GET | `/collection/collections/:id/evidences` | Autenticado | Lista evidências da coleta |
| POST | `/collection/collections/:id/evidences` | Autenticado | Adiciona evidência: `{ descricao, arquivo_url }` |

**Serializer RegistroColeta:**
```json
{
  "id": 1,
  "id_microservico": "string (UUID do MS)",
  "imovel": 1,
  "pontuacao": "10.50",
  "data_hora_coleta": "2026-05-19T10:00:00Z",
  "peso_kg": "2.500"
}
```

---

### 2.12 Contestações (`/api/collection/disputes`)

| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| GET | `/collection/disputes` | Autenticado | Lista; morador vê apenas as suas. Filtro: `status` |
| POST | `/collection/disputes` | **Morador** | Abre contestação: `{ coleta, motivo }` |
| GET | `/collection/disputes/:pk` | Autenticado | Detalhe |
| PATCH | `/collection/disputes/:pk` | **Gestor** | Analisa: `{ status, resposta }` |

**Serializer Contestacao:**
```json
{
  "id": 1,
  "coleta": 1,
  "aberta_por": 5,
  "motivo": "string",
  "status": "aberta | em_analise | aceita | negada",
  "analisada_por": 1,
  "resposta": "string",
  "aberta_em": "2026-05-19T10:00:00Z",
  "atualizada_em": "2026-05-19T12:00:00Z"
}
```

---

### 2.13 Auditoria (`/api/audit/`) — apenas `gestor`

| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/audit/logs` | Lista logs. Filtros: `usuario_id`, `tabela`, `operacao`, `data_inicio`, `data_fim`, `objeto_id` |
| GET | `/audit/logs/export?formato=csv` | Download CSV com os mesmos filtros |

**Serializer AuditLog:**
```json
{
  "id": 1,
  "timestamp": "2026-05-19T10:00:00Z",
  "usuario_id": 1,
  "usuario_email": "string",
  "operacao": "INSERT | UPDATE | DELETE | SELECT",
  "tabela": "string",
  "objeto_id": "string",
  "dados_antes": {},
  "dados_depois": {},
  "ip_origem": "string",
  "endpoint": "string"
}
```

---

### 2.14 Relatórios LLM (`/api/reports/`) — apenas `gestor`

| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/reports/generate` | Gera relatório narrativo via DeepSeek/LM Studio |
| GET | `/reports/history` | Histórico de relatórios gerados. Filtro: `tipo`, `programa_id` |

**POST `/reports/generate` — Request:**
```json
{
  "tipo": "participacao | impacto | ranking | auditoria",
  "periodo": { "inicio": "2026-01-01", "fim": "2026-05-31" },
  "programa_id": 1
}
```

**Response 201:**
```json
{
  "id": 1,
  "tipo": "string",
  "periodo": { "inicio": "2026-01-01", "fim": "2026-05-31" },
  "programa": 1,
  "relatorio": "texto narrativo gerado pelo LLM",
  "tokens_utilizados": 1500,
  "gerado_em": "2026-05-19T10:00:00Z",
  "gerado_por": 1
}
```

---

## 3. Endpoints do Microserviço de Coleta (cp-collection-ms)

> Base: `http://localhost:8002/api`  
> Auth própria: JWT com `matricula` + `senha` (coletor de campo, não é o usuário da plataforma web).  
> **⚠️ Nenhum desses endpoints é chamado pelo frontend web atualmente.**

### 3.1 Autenticação do Coletor

| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| POST | `/auth/register` | Nenhuma | Cadastra coletor: `{ matricula, senha, nome, email, zona, cargo }` |
| POST | `/auth/login` | Nenhuma | Login: `{ matricula, senha }` → `{ token, user }` |
| POST | `/auth/logout` | Bearer | Simbólico (tokens não são invalidados) |
| GET | `/me` | Bearer | Dados do coletor logado |

**Response de login:**
```json
{
  "token": "string (JWT)",
  "user": {
    "id": "ObjectId",
    "nome": "string",
    "matricula": "string",
    "email": "string",
    "avatar_url": "string | null",
    "zona": "string",
    "role": "coletor"
  }
}
```

---

### 3.2 Busca de Imóveis

| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| GET | `/imoveis/buscar` | Bearer | Busca por `tipo` (`numero`, `qrcode`, `endereco`) + `valor` |
| GET | `/imoveis/proximos` | Bearer | Imóveis próximos: `lat`, `lng`, `raio` (metros, default 200) |
| GET | `/imoveis/:pk` | Bearer | Detalhe por ObjectId (inclui histórico de coletas) |

**GET `/imoveis/proximos` — Response:**
```json
{
  "imoveis": [
    {
      "id": "ObjectId",
      "id_externo": "inscricao_imobiliaria",
      "logradouro": "string",
      "numero": "string",
      "bairro": "string",
      "elegivel": true,
      "distancia": 45.3,
      "coletado_hoje": false,
      "location": { "type": "Point", "coordinates": [-38.54, -3.71] }
    }
  ],
  "total": 5
}
```

---

### 3.3 Registro de Coletas

| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| POST | `/coletas` | Bearer | Registra coleta (suporta multipart para foto) |
| GET | `/coletas/historico` | Bearer | Histórico do coletor logado. Filtros: `tipo_periodo`, `data`, `page`, `limit` |
| GET | `/coletas/pendentes` | Bearer | Coletas não sincronizadas com o Core |
| GET | `/coletas/:pk` | Bearer | Detalhe por ObjectId |

**POST `/coletas` — Request:**
```json
{
  "imovel_id": "ObjectId",
  "peso_total_kg": "2.500",
  "data_hora": "2026-05-19T10:00:00Z",
  "observacoes": "",
  "offline_id": "UUID | null"
}
```

**Response 201:**
```json
{
  "id": "ObjectId",
  "codigo": "ABCD-1234",
  "imovel_id": "ObjectId",
  "coletor_id": "ObjectId",
  "status": "confirmada",
  "data_hora": "2026-05-19T10:00:00Z",
  "peso_total_kg": "2.500",
  "foto_url": "http://minio/coletas/uuid.jpg",
  "offline_id": "UUID | null",
  "sincronizado": true
}
```

---

### 3.4 Sincronização Offline

| Método | Endpoint | Auth | Descrição |
|---|---|---|---|
| POST | `/sincronizar` | Bearer | Batch de coletas offline: `{ coletas: [...] }` → 200 ou 207 (parcial) |
| GET | `/sincronizacao/status` | Bearer | Status de sincronização do coletor |

---

## 4. Contrato RabbitMQ

### Fila `imoveis` — Core → MS de Coleta

Publicada pelo Core a cada save de `Imovel`. Consumida pelo MS via `python manage.py consumir_imoveis`.

```json
{
  "inscricao_imobiliaria": "string (id_externo no MS)",
  "nome": "string",
  "cpf": "string | null",
  "endereco": "string",
  "numero": "string",
  "complemento": "string",
  "bairro": "string",
  "iptu": "string",
  "telefone": "string",
  "latitude": -3.7172,
  "longitude": -38.5433,
  "elegivel": true,
  "motivo_inelegivel": "",
  "ativo": true,
  "acao": "adesao_programa | atualizacao_imovel"
}
```

### Fila `coletas` — MS de Coleta → Core

Publicada pelo MS após cada coleta confirmada. Consumida pelo Core via `python manage.py consume_queue`.

```json
{
  "coleta_id": "string (ObjectId do MS → vira id_microservico no Core)",
  "inscricao_imobiliaria": "string",
  "peso_total_kg": "2.500",
  "data_hora": "2026-05-19T10:00:00+00:00"
}
```

**Processamento no Core:** `pontos = peso_kg × ConstantePontuacao.pontos_por_kg`. Deduplicação por `id_microservico`.

---

## 5. Endpoints Faltantes

Esta seção mapeia lacunas: funcionalidades esperadas pelo frontend (via types, sidebar e páginas stub) que ainda não têm chamadas de API implementadas.

### 5.1 Middleware de refresh de token não está wired

**Problema:** `proxy.ts` implementa a lógica de renovação automática, mas Next.js requer que o middleware esteja em `middleware.ts`. Sem isso, sessões expiram e não se renovam.

**Solução necessária:** Renomear/mover `proxy.ts` para `middleware.ts` na raiz do projeto.

---

### 5.2 Logout não invalida o refresh token no servidor

**Problema:** `POST /api/accounts/auth/logout` exige `{ "refresh": "string" }` no body para blacklistar o token, mas `logoutAction` não envia esse campo.

**Solução necessária:** Enviar o `refreshToken` do cookie no body do logout.

---

### 5.3 Páginas de dashboard sem dados (stubs)

Todas as páginas listadas no Sidebar estão implementadas como `<h1>` sem nenhuma chamada de API. Os tipos TypeScript em `types/entities/` já definem as estruturas esperadas.

| Rota | Perfil | Endpoint(s) necessário(s) no Core | Status |
|---|---|---|---|
| `/meu-imovel` | morador | `GET /api/program/properties` (filtrado) | ❌ não implementado |
| `/coletas` (morador) | morador | `GET /api/collection/collections` | ❌ não implementado |
| `/beneficios` (morador) | morador | `GET /api/accounts/me/benefits` | ❌ não implementado |
| `/contestacoes` (morador) | morador | `GET /api/collection/disputes`, `POST /api/collection/disputes` | ❌ não implementado |
| `/imoveis` (supervisor) | supervisor | `GET /api/program/properties` | ❌ não implementado |
| `/coletas` (supervisor) | supervisor | `GET /api/collection/collections` | ❌ não implementado |
| `/constante-pontuacao` | supervisor | `GET /api/program/scoring-constant`, `PATCH /api/program/scoring-constant` | ❌ não implementado |
| `/relatorios` (supervisor) | supervisor | `GET /api/program/reports/*` | ❌ não implementado |
| `/beneficios` (supervisor) | supervisor | `GET /api/program/benefits` | ❌ não implementado |
| `/usuarios` | gestor | `GET /api/accounts/users`, CRUD | ❌ não implementado |
| `/imoveis` (gestor) | gestor | `GET /api/program/properties`, CRUD | ❌ não implementado |
| `/programas` | gestor | `GET /api/program/programs`, CRUD + regras | ❌ não implementado |
| `/coletas` (gestor) | gestor | `GET /api/collection/collections` | ❌ não implementado |
| `/contestacoes` (gestor) | gestor | `GET /api/collection/disputes`, `PATCH /api/collection/disputes/:pk` | ❌ não implementado |
| `/consolidacao` | gestor | `POST /api/program/consolidations/run`, `GET /api/program/consolidations` | ❌ não implementado |
| `/relatorios` (gestor) | gestor | `GET /api/program/reports/*`, `POST /api/reports/generate` | ❌ não implementado |
| `/auditoria` | gestor | `GET /api/audit/logs`, export CSV | ❌ não implementado |
| `/perfil` | todos | `GET /api/accounts/auth/me`, `PATCH /api/accounts/auth/me` | ❌ não implementado |

---

### 5.4 Integração com o Microserviço de Coleta ausente no Frontend

O frontend web nunca chama o `cp-collection-ms`. A variável `COLLECTION_API_URL` está no `.env.example` mas não é referenciada em nenhum arquivo fonte.

**Casos de uso que provavelmente precisariam de integração direta (ou via Core):**

| Funcionalidade | Endpoint MS | Observação |
|---|---|---|
| Painel de coletas por coletor | `GET /api/coletas/historico` | Acesso direto ao MS ou via Core |
| Status de sincronização | `GET /api/sincronizacao/status` | Exclusivo do MS |
| Busca de imóveis por GPS | `GET /api/imoveis/proximos` | Exclusivo do MS |

> O fluxo esperado é que o **app mobile** (não este frontend web) seja o cliente do MS de Coleta. O frontend web consome os dados já processados pelo Core via fila RabbitMQ.

---

### 5.5 Endpoint de perfil do usuário não expõe foto/avatar

O Core (`GET /api/accounts/auth/me`) não retorna URL de foto de perfil. O MS tem `foto_perfil` no modelo `Coletor`, mas são sistemas de usuário separados.

---

### 5.6 Discrepância no contrato RabbitMQ (coletas)

`teste_mq.py` no MS indica que o Core espera campos `pontuacao` e `imovel_id` na mensagem da fila `coletas`, mas o publisher atual (`coleta/services/fila.py`) envia apenas `coleta_id`, `inscricao_imobiliaria`, `peso_total_kg` e `data_hora`. O Core calcula a pontuação internamente com base na `ConstantePontuacao`, então essa discrepância pode ser intencional, mas vale revisão.
