# Roteiro manual de teste — `gerente_geral` e escopo por cidade

Roteiro passo a passo com `curl` para validar manualmente, contra o `core`
rodando localmente, as regras de negócio do perfil `gerente_geral` e do
escopo por cidade de `gestor`/`supervisor`. Ver `docs/gerente_geral_endpoints.md`
para a referência completa de cada endpoint.

**Pré-requisitos:**
- `docker compose up -d core core-db` (containers saudáveis).
- `curl` e `jq` instalados (`jq` só para extrair campos das respostas — se não
  tiver, leia o JSON manualmente).

```bash
BASE_URL="http://localhost:8001/api"
```

---

## Passo 1 — Bootstrap do primeiro `gerente_geral`

Não existe endpoint público para criar o primeiro `gerente_geral` (o
autocadastro em `/auth` só cria `morador`, e criar um `gerente_geral` via
`/users` exige já ser `gestor` ou `gerente_geral`). Para o primeiro usuário,
crie via shell do Django:

```bash
docker compose exec core python manage.py shell -c "
from accounts.models import Usuario
u = Usuario(email='geral@ex.com', nome='Gerente Geral', perfil='gerente_geral', is_staff=True, is_superuser=True)
u.set_password('senha1234')
u.save()
print('criado, id=', u.id)
"
```
**Esperado:** imprime `criado, id= <N>` sem erro (o `clean()` do model não
bloqueia `gerente_geral` sem cidade, pois esse perfil não está em
`PERFIS_COM_CIDADE_OBRIGATORIA`).

## Passo 2 — Login do `gerente_geral`

```bash
curl -s -X POST $BASE_URL/token/ \
  -H 'Content-Type: application/json' \
  -d '{"email":"geral@ex.com","password":"senha1234"}'
```
**Esperado:** `200 OK`, body `{"refresh": "...", "access": "..."}`.

```bash
TOKEN_GERAL=$(curl -s -X POST $BASE_URL/token/ -H 'Content-Type: application/json' \
  -d '{"email":"geral@ex.com","password":"senha1234"}' | jq -r .access)
```

## Passo 3 — Catálogo de cidades vazio

```bash
curl -s $BASE_URL/accounts/cidades -H "Authorization: Bearer $TOKEN_GERAL"
```
**Esperado:** `200 OK`, `[]`.

## Passo 4 — `gerente_geral` cria duas cidades

```bash
curl -s -X POST $BASE_URL/accounts/cidades \
  -H "Authorization: Bearer $TOKEN_GERAL" -H 'Content-Type: application/json' \
  -d '{"nome":"Fortaleza","uf":"CE"}'

curl -s -X POST $BASE_URL/accounts/cidades \
  -H "Authorization: Bearer $TOKEN_GERAL" -H 'Content-Type: application/json' \
  -d '{"nome":"Sobral","uf":"CE"}'
```
**Esperado (ambas):** `201 Created`, ex.: `{"id":1,"nome":"Fortaleza","uf":"CE","ativo":true}`.

```bash
CIDADE_FORTALEZA=1   # ajuste conforme o id retornado
CIDADE_SOBRAL=2       # ajuste conforme o id retornado
```

## Passo 5 — `gerente_geral` cria um gestor para Fortaleza

```bash
curl -s -X POST $BASE_URL/accounts/users \
  -H "Authorization: Bearer $TOKEN_GERAL" -H 'Content-Type: application/json' \
  -d "{\"email\":\"gestor.fortaleza@ex.com\",\"cpf\":\"111.111.111-11\",\"nome\":\"Gestor Fortaleza\",\"perfil\":\"gestor\",\"cidade\":$CIDADE_FORTALEZA,\"password\":\"senha1234\"}"
```
**Esperado:** `201 Created`, `{"email":"gestor.fortaleza@ex.com","cpf":"111.111.111-11","nome":"Gestor Fortaleza","perfil":"gestor","cidade":1}` (sem `id`, o serializer de criação não o expõe).

Login desse gestor:
```bash
TOKEN_GESTOR_FORT=$(curl -s -X POST $BASE_URL/token/ -H 'Content-Type: application/json' \
  -d '{"email":"gestor.fortaleza@ex.com","password":"senha1234"}' | jq -r .access)
```

## Passo 6 — Gestor NÃO pode criar/editar cidade

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST $BASE_URL/accounts/cidades \
  -H "Authorization: Bearer $TOKEN_GESTOR_FORT" -H 'Content-Type: application/json' \
  -d '{"nome":"Juazeiro do Norte","uf":"CE"}'
```
**Esperado:** `403` (só `IsGerenteGeral`; `GET` continua liberado para qualquer autenticado).

## Passo 7 — Gestor cria outro gestor: cidade é forçada para a do gestor

Envie propositalmente a cidade de Sobral no corpo — o resultado deve vir
com a cidade do gestor (Fortaleza), ignorando o valor enviado:

```bash
curl -s -X POST $BASE_URL/accounts/users \
  -H "Authorization: Bearer $TOKEN_GESTOR_FORT" -H 'Content-Type: application/json' \
  -d "{\"email\":\"outro.gestor@ex.com\",\"cpf\":\"222.222.222-22\",\"nome\":\"Outro Gestor\",\"perfil\":\"gestor\",\"cidade\":$CIDADE_SOBRAL,\"password\":\"senha1234\"}"
```
**Esperado:** `201 Created`, `"cidade": 1` (id de Fortaleza), mesmo tendo
enviado `$CIDADE_SOBRAL` no corpo.

## Passo 7b — Gestor NÃO pode criar/promover para `gerente_geral`

```bash
curl -s -X POST $BASE_URL/accounts/users \
  -H "Authorization: Bearer $TOKEN_GESTOR_FORT" -H 'Content-Type: application/json' \
  -d '{"email":"outro.geral@ex.com","cpf":"999.999.999-99","nome":"Outro Geral","perfil":"gerente_geral","password":"senha1234"}'
```
**Esperado:** `400 Bad Request`,
```json
{"perfil": ["Um gestor não pode criar ou promover usuários para gerente_geral."]}
```
(A permissão `IsGestor` deixa passar — o bloqueio é da validação do serializer.)

## Passo 8 — Gestor cria supervisor: cidade é forçada para a do gestor

Envie propositalmente a cidade de Sobral no corpo — o resultado deve vir
com a cidade do gestor (Fortaleza), ignorando o valor enviado:

```bash
curl -s -X POST $BASE_URL/accounts/users \
  -H "Authorization: Bearer $TOKEN_GESTOR_FORT" -H 'Content-Type: application/json' \
  -d "{\"email\":\"supervisor.fortaleza@ex.com\",\"cpf\":\"333.333.333-33\",\"nome\":\"Supervisor Fortaleza\",\"perfil\":\"supervisor\",\"cidade\":$CIDADE_SOBRAL,\"password\":\"senha1234\"}"
```
**Esperado:** `201 Created`, `"cidade": 1` (id de Fortaleza), mesmo tendo
enviado `$CIDADE_SOBRAL` no corpo.

## Passo 9 — Autocadastro público sempre cria `morador`

```bash
curl -s -X POST $BASE_URL/accounts/auth \
  -H 'Content-Type: application/json' \
  -d '{"email":"morador1@ex.com","cpf":"444.444.444-44","nome":"Morador Um","password":"senha1234","perfil":"gerente_geral"}'
```
**Esperado:** `201 Created`, `{"email":"morador1@ex.com","cpf":"444.444.444-44","nome":"Morador Um"}` —
note que **não há campo `perfil` na resposta** e, mesmo enviando
`"perfil":"gerente_geral"` no corpo, o usuário é criado como `morador`
(confirme consultando `/accounts/users?search=morador1` autenticado como
gestor/gerente_geral).

```bash
TOKEN_MORADOR1=$(curl -s -X POST $BASE_URL/token/ -H 'Content-Type: application/json' \
  -d '{"email":"morador1@ex.com","password":"senha1234"}' | jq -r .access)
```

## Passo 10 — Validação de cidade no cadastro de imóvel

Tentando uma cidade inexistente no catálogo:
```bash
curl -s -X POST $BASE_URL/program/properties \
  -H "Authorization: Bearer $TOKEN_MORADOR1" -H 'Content-Type: application/json' \
  -d '{"inscricao":"IMV-001","titular": <id_morador1>,"cep":"60000-000","logradouro":"Rua A","numero":"100","bairro":"Centro","cidade":"Recife","estado":"PE","num_moradores":1}'
```
**Esperado:** `400 Bad Request`,
```json
{"cidade": ["Cidade não cadastrada ou inativa. Selecione uma das cidades disponíveis."]}
```
(Substitua `<id_morador1>` pelo id retornado em `GET /accounts/auth/me` com `$TOKEN_MORADOR1`.)

Agora com uma cidade válida:
```bash
curl -s -X POST $BASE_URL/program/properties \
  -H "Authorization: Bearer $TOKEN_MORADOR1" -H 'Content-Type: application/json' \
  -d '{"inscricao":"IMV-001","titular": <id_morador1>,"cep":"60000-000","logradouro":"Rua A","numero":"100","bairro":"Centro","cidade":"Fortaleza","estado":"CE","num_moradores":1}'
```
**Esperado:** `201 Created`. Anote o `id` retornado como `IMOVEL_FORTALEZA`.

## Passo 11 — Escopo por cidade nas listagens (gestor vs. gerente_geral)

Gestor de Fortaleza vê o imóvel recém-criado:
```bash
curl -s $BASE_URL/program/properties -H "Authorization: Bearer $TOKEN_GESTOR_FORT"
```
**Esperado:** `200 OK`, lista contendo `IMOVEL_FORTALEZA`.

Crie e logue um gestor de Sobral (repita o Passo 5 usando `$TOKEN_GERAL`,
`perfil":"gestor"` e `cidade":$CIDADE_SOBRAL`, depois faça login como
`TOKEN_GESTOR_SOBRAL`). Esse gestor **não** deve ver o imóvel de Fortaleza:
```bash
curl -s $BASE_URL/program/properties -H "Authorization: Bearer $TOKEN_GESTOR_SOBRAL"
```
**Esperado:** `200 OK`, lista **vazia** (`[]` ou `"results": []` se paginado).

`gerente_geral` vê todos, de qualquer cidade:
```bash
curl -s $BASE_URL/program/properties -H "Authorization: Bearer $TOKEN_GERAL"
```
**Esperado:** `200 OK`, lista contendo `IMOVEL_FORTALEZA` (e qualquer outro imóvel de qualquer cidade).

## Passo 12 — Escopo por cidade no acesso direto por id (defesa em profundidade)

Gestor de Sobral tentando acessar diretamente o imóvel de Fortaleza pelo id:
```bash
curl -s -o /dev/null -w '%{http_code}\n' \
  $BASE_URL/program/properties/$IMOVEL_FORTALEZA \
  -H "Authorization: Bearer $TOKEN_GESTOR_SOBRAL"
```
**Esperado:** `403` (bloqueado mesmo sabendo o id — `get_object()` valida a cidade).

`gerente_geral` acessando o mesmo imóvel:
```bash
curl -s -o /dev/null -w '%{http_code}\n' \
  $BASE_URL/program/properties/$IMOVEL_FORTALEZA \
  -H "Authorization: Bearer $TOKEN_GERAL"
```
**Esperado:** `200`.

## Passo 13 — Mesmo padrão em coletas e contestações

O mesmo escopo por cidade (lista filtrada para gestor/supervisor, acesso
direto por id bloqueado com `403`, sem restrição para `gerente_geral`) se
aplica a:
- `GET /collection/collections` e `GET /collection/collections/:id`
- `GET /collection/disputes` e `GET/PATCH /collection/disputes/:id`
- `GET /program/benefits`
- `GET /program/reports/participation`, `/reports/ranking`, `/reports/impact`

Repita os Passos 11 e 12 trocando a URL por cada um dos endpoints acima
(um registro de coleta e uma contestação precisam existir vinculados a
`IMOVEL_FORTALEZA` — normalmente chegam pela fila do RabbitMQ, mas também
podem ser criados diretamente via `POST /collection/collections` como
`gestor`/`supervisor`/`gerente_geral`) para confirmar o mesmo comportamento.

## Passo 14 — Limpeza (opcional)

```bash
docker compose exec core python manage.py shell -c "
from accounts.models import Usuario
Usuario.objects.filter(email__in=[
    'geral@ex.com','gestor.fortaleza@ex.com','outro.gestor@ex.com',
    'outro.geral@ex.com','supervisor.fortaleza@ex.com','morador1@ex.com',
]).delete()
"
```
