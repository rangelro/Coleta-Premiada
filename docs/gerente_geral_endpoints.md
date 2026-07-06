# Endpoints afetados pelo perfil `gerente_geral` e por cidade

Documentação dos endpoints do **core** (Django/DRF) que mudaram de comportamento
com a introdução do perfil `gerente_geral` e do modelo `Cidade`. Cobre apenas
os endpoints impactados — para o restante da API, ver `API_MAPPING.md`.

Base URL local: `http://localhost:8001/api`
Autenticação: JWT via header `Authorization: Bearer <access_token>`
(obtido em `POST /api/token/` com `{"email": "...", "password": "..."}`).

## Hierarquia de perfis

| Perfil | Cidade própria? | Observação |
|---|---|---|
| `morador` | Não (escolhe cidade por imóvel) | Sem mudança de permissão |
| `gestor` | Sim, obrigatória | Escopado à própria cidade nas listagens/ações administrativas |
| `supervisor` | Sim, obrigatória | Escopado à própria cidade nas listagens/ações administrativas |
| `gerente_geral` (novo) | Não tem — enxerga todas as cidades | Superior a gestor/supervisor: onde a permissão exigia `gestor`, `supervisor` ou `gestor OR supervisor`, `gerente_geral` também é aceito automaticamente |

Um `gestor` **não pode** criar/promover ninguém para `gerente_geral` via
`POST/PATCH /users`. Um `gestor` criando/promovendo um `gestor` ou um
`supervisor` tem a cidade do novo usuário **forçada** para a própria cidade
do gestor (o valor de `cidade` enviado no corpo é ignorado nesse caso).

---

## `/api/accounts` — Usuários, Cidades e Roles

### `POST /api/accounts/auth`
Cadastro público (sem autenticação). **Sempre cria `perfil='morador'`** —
não é mais possível se autocadastrar como gestor/supervisor/gerente_geral.

- **Perfil exigido:** nenhum (`AllowAny`)
- **Body:**
  ```json
  { "email": "morador@ex.com", "cpf": "123.456.789-00", "nome": "Fulano", "password": "senha1234" }
  ```
- **201 Created:**
  ```json
  { "email": "morador@ex.com", "cpf": "123.456.789-00", "nome": "Fulano" }
  ```
- **Observação:** a resposta não inclui `id` (o serializer de criação não expõe
  esse campo). Para obter o id do usuário criado, faça login e consulte
  `GET /auth/me`, ou, se autenticado como gestor/gerente_geral, use
  `GET /users?search=<email>`.
- **400** se `perfil` for enviado no corpo — o campo simplesmente é ignorado
  (não existe no serializer), o registro sempre sai como `morador`.

### `POST /api/accounts/users`
Cria usuário com qualquer perfil. Usado por gestor/gerente_geral.

- **Perfil exigido:** `gestor` ou `gerente_geral` (`IsGestor`)
- **Body:**
  ```json
  {
    "email": "gestor.fortaleza@ex.com",
    "cpf": "111.111.111-11",
    "nome": "Gestora Fortaleza",
    "perfil": "gestor",
    "cidade": 1,
    "password": "senha1234"
  }
  ```
  - `cidade`: obrigatório (PK de `Cidade`) se `perfil` for `gestor` ou
    `supervisor`; deve ser omitido/`null` para `morador` e `gerente_geral`.
- **201 Created:** mesmos campos do body, sem `password` e sem `id`.
- **400** possíveis:
  - `{"cidade": ["Cidade obrigatória para o perfil informado."]}`
  - `{"cidade": ["Esse perfil não deve ter cidade própria."]}` (ex: perfil `gerente_geral` com `cidade` preenchida)
  - `{"perfil": ["Um gestor não pode criar ou promover usuários para gerente_geral."]}` — só ocorre quando quem faz a requisição é `gestor` (não se aplica a `gerente_geral`)
- **Observação:** se quem chama for `gestor` e `perfil='gestor'` ou
  `perfil='supervisor'`, o `cidade` enviado é **substituído silenciosamente**
  pela cidade do próprio gestor (não gera erro) — um gestor só cria/promove
  gestores e supervisores para a própria cidade.

### `GET /api/accounts/users`
- **Perfil exigido:** `gestor` ou `gerente_geral`
- **Query params:** `perfil`, `ativo` (`true`/`false`), `search` (nome/email), paginação (`page`, `page_size`, máx. 100)
- **200 OK:** lista paginada de `UsuarioSerializer` — agora inclui `cidade` aninhada:
  ```json
  { "id": 5, "email": "g@ex.com", "cpf": "...", "nome": "...", "perfil": "gestor",
    "cidade": {"id": 1, "nome": "Fortaleza", "uf": "CE", "ativo": true},
    "ativo": true, "roles": [] }
  ```
- **Observação:** não há escopo por cidade nesta listagem — qualquer gestor/
  supervisor/gerente_geral autenticado vê todos os usuários do sistema
  (o escopo por cidade foi aplicado apenas aos dados operacionais: imóveis,
  coletas, contestações, benefícios e relatórios).

### `GET/PATCH/DELETE /api/accounts/users/:id`
- **Perfil exigido:** `gestor` ou `gerente_geral`
- **PATCH body** (`UsuarioManagerUpdateSerializer`): qualquer subconjunto de
  `{"nome", "cpf", "perfil", "cidade", "ativo"}`. Mesmas validações de
  cidade/hierarquia do POST acima, mas considerando o estado atual do usuário
  quando um campo não é enviado (ex.: PATCH só de `nome` em um gestor não
  exige reenviar `cidade`).
- **DELETE:** soft-delete (`ativo=False`). Gestor/gerente_geral não pode
  desativar a própria conta (`403`).

### `GET /api/accounts/roles`, `POST /api/accounts/roles` (só `gestor`/`gerente_geral` no POST)
### `GET/PATCH /api/accounts/roles/:id` (PATCH só `gestor`/`gerente_geral`)
### `POST/DELETE /api/accounts/users/:id/roles/:roleId` (só `gestor`/`gerente_geral`)
Sem mudança de schema — apenas passaram a aceitar `gerente_geral` por causa
do broadening de `IsGestor`.

### `GET /api/accounts/cidades`
Catálogo de cidades atendidas.
- **Perfil exigido:** qualquer autenticado
- **200 OK:**
  ```json
  [{"id": 1, "nome": "Fortaleza", "uf": "CE", "ativo": true}, ...]
  ```

### `POST /api/accounts/cidades` (novo endpoint)
- **Perfil exigido:** somente `gerente_geral`
- **Body:** `{"nome": "Sobral", "uf": "CE", "ativo": true}`
- **201 Created:** o mesmo objeto com `id`.
- **400:** `{"nome": ["cidade com este nome já existe."]}` se duplicado.

### `PATCH /api/accounts/cidades/:id` (novo endpoint)
- **Perfil exigido:** somente `gerente_geral`
- **Body:** qualquer subconjunto de `{"nome", "uf", "ativo"}`.
- **Observação:** desativar uma cidade (`ativo=false`) não afeta usuários já
  vinculados a ela, mas passa a bloquear `validate_cidade` de `Imovel` para
  novos cadastros de imóvel nessa cidade.

### `GET/PATCH/DELETE /api/accounts/auth/me`
Sem mudança de schema relevante — `GET` agora retorna `cidade` aninhada
(nula para morador/gerente_geral, preenchida para gestor/supervisor).

---

## `/api/program` — Imóveis, Programas, Benefícios, Relatórios

`Imovel.cidade` continua sendo um `CharField` livre (não uma FK) — a
validação passou a checar contra o catálogo `Cidade`, mas o dado em si segue
sendo uma string (ex.: `"Fortaleza"`), igual antes.

### `POST /api/program/properties`
- **Perfil exigido:** qualquer autenticado
- **Body (relevante):** `{"cidade": "Fortaleza", "bairro": "Centro", ...}`
- **400 novo:** `{"cidade": ["Cidade não cadastrada ou inativa. Selecione uma das cidades disponíveis."]}` se o valor não bater com uma `Cidade` ativa cadastrada em `/accounts/cidades`.

### `GET /api/program/properties`
- **Perfil exigido:** qualquer autenticado
- **Escopo por cidade (novo):**
  - `morador`: vê só os próprios imóveis (sem mudança).
  - `gestor`/`supervisor`: veem **somente imóveis cuja `cidade` bate com a
    cidade do usuário logado**. Se o usuário não tiver `cidade` definida,
    a lista volta vazia.
  - `gerente_geral`: vê todos os imóveis, de todas as cidades.
- Filtros `bairro`, `cidade` (icontains), `ativo`, `search` continuam
  funcionando por cima do escopo acima.

### `GET/PATCH /api/program/properties/:id`
- **Perfil exigido:** GET qualquer autenticado; PATCH `gestor`/`supervisor`/`gerente_geral`
- **403 novo:** se `gestor`/`supervisor` tentar acessar (GET ou PATCH) um
  imóvel de cidade diferente da sua, retorna `permission_denied` (403),
  mesmo sabendo o `id`.

### `POST /api/program/properties/:id/users` e `DELETE /api/program/properties/:id/users/:userId`
- **Perfil exigido:** `gestor`/`supervisor`/`gerente_geral`
- **403 novo:** mesma checagem de cidade do item acima antes de vincular/
  desvincular um morador.

### `GET /api/program/benefits`
- **Perfil exigido:** `gestor`/`supervisor`/`gerente_geral`
- **Escopo por cidade (novo):** gestor/supervisor só veem saldos
  (`SaldoPontos`) de imóveis da própria cidade; gerente_geral vê todos.
- Filtros `imovel_id`, `programa_id`, `ciclo` continuam disponíveis.

### `GET /api/program/reports/participation`, `/reports/ranking`, `/reports/impact`
- **Perfil exigido:** `gestor`/`supervisor`/`gerente_geral`
- **Escopo por cidade (novo):** os três relatórios agora agregam apenas
  coletas/saldos de imóveis da cidade do gestor/supervisor; gerente_geral
  continua vendo os números agregados do sistema inteiro.

### Demais endpoints de `program` (`/programs`, `/programs/:id/rules`, `/consolidations/*`, `/scoring-constant`)
Sem mudança de schema — apenas herdam o broadening de `IsGestor`/
`IsSupervisor`/`IsGestorOrSupervisor` (gerente_geral passa a ter acesso onde
antes só gestor/supervisor tinham). **Não são escopados por cidade**:
`ConsolidacaoRunView`/`ConsolidacaoListView` operam sobre o programa inteiro
(processo em lote sem recorte natural por cidade) e `ConstantePontuacaoView`
é uma constante global do sistema.

---

## `/api/collection` — Coletas e Contestações

### `GET/POST /api/collection/collections`
- **Perfil exigido:** GET qualquer autenticado; POST `gestor`/`supervisor`/`gerente_geral`
- **Escopo por cidade (novo) no GET:** morador vê só coletas dos próprios
  imóveis (sem mudança); gestor/supervisor veem só coletas de imóveis da
  própria cidade (via `imovel__cidade`); gerente_geral vê todas.

### `GET /api/collection/collections/:id`
- **403 novo:** gestor/supervisor não conseguem mais abrir o detalhe de uma
  coleta de outra cidade mesmo sabendo o `id`.

### `GET/POST /api/collection/disputes`
- **Perfil exigido:** GET qualquer autenticado; POST somente `morador`
- **Escopo por cidade (novo) no GET:** morador vê só as próprias contestações
  (sem mudança); gestor/supervisor veem só contestações cuja coleta pertence
  a um imóvel da própria cidade; gerente_geral vê todas.

### `GET/PATCH /api/collection/disputes/:id`
- **Perfil exigido:** PATCH somente `gestor` ou `gerente_geral`
- **403 novo:** gestor não consegue mais analisar/responder (`PATCH`) uma
  contestação de outra cidade, mesmo sabendo o `id`. `gerente_geral` pode
  analisar contestações de qualquer cidade.

### `GET/POST /api/collection/collections/:id/evidences`
Sem mudança — não é escopado por cidade (segue a mesma regra de acesso da
coleta pai, mas o *endpoint* de evidências em si não filtra por cidade).
