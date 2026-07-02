# Documentação de Endpoints – Coleta Premiada

Este documento detalha todos os endpoints HTTP expostos e consumidos pelo ecossistema **Coleta Premiada**, cobrindo o **Core API (Django + DRF)**, o **MS de Coleta (Django + MongoDB)**, o **Serviço de Auditoria**, o **Serviço de Relatórios LLM** e os contratos de mensageria **RabbitMQ**.

---

## ─── CORE API (Porta 8001) ───

Base URL: `http://localhost:8001/api`  
Autenticação: Bearer JWT (`Authorization: Bearer <token>`)

---

### 1. Autenticação & Conta

#### POST `/token/`
**Descrição:** Autentica o usuário na plataforma e gera os tokens JWT.
*   **Autenticação:** Nenhuma.
*   **Request Body:**
    | Campo | Tipo | Obrigatório | Descrição |
    |---|---|---|---|
    | `email` | `string` | Sim | E-mail cadastrado do usuário |
    | `password` | `string` | Sim | Senha do usuário |

    ```json
    {
      "email": "morador@coleta.com",
      "password": "senha"
    }
    ```
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "access": "eyJhbGciOi...",
          "refresh": "eyJhbGciOi..."
        }
        ```
    *   `401 Unauthorized`:
        ```json
        {
          "detail": "No active account found with the given credentials"
        }
        ```

#### POST `/token/refresh/`
**Descrição:** Renova o token de acesso expirado.
*   **Autenticação:** Nenhuma.
*   **Request Body:**
    | Campo | Tipo | Obrigatório | Descrição |
    |---|---|---|---|
    | `refresh` | `string` | Sim | Token JWT de refresh ativo |

    ```json
    {
      "refresh": "refresh_token_string"
    }
    ```
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "access": "new_access_token_string",
          "refresh": "new_refresh_token_string"
        }
        ```
    *   `401 Unauthorized` (Token inválido/expirado):
        ```json
        {
          "detail": "Token is invalid or expired",
          "code": "token_not_valid"
        }
        ```

#### GET `/accounts/auth/me`
**Descrição:** Obtém os dados cadastrais do usuário autenticado.
*   **Autenticação:** Bearer JWT.
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "id": 2,
          "email": "morador@coleta.com",
          "cpf": "12345678901",
          "nome": "João Silva",
          "perfil": "morador",
          "ativo": true,
          "roles": []
        }
        ```
    *   `401 Unauthorized` (Token expirado/ausente):
        ```json
        {
          "detail": "As credenciais de autenticação não foram fornecidas."
        }
        ```

#### PATCH `/accounts/auth/me`
**Descrição:** Atualiza nome e CPF do próprio usuário logado.
*   **Autenticação:** Bearer JWT.
*   **Request Body:**
    | Campo | Tipo | Obrigatório | Descrição |
    |---|---|---|---|
    | `nome` | `string` | Não | Novo nome completo |
    | `cpf` | `string` | Não | CPF com 11 dígitos numéricos |

    ```json
    {
      "nome": "João Silva Alterado",
      "cpf": "98765432109"
    }
    ```
*   **Respostas:**
    *   `200 OK`: Dados de usuário atualizados (retorna objeto User completo).
    *   `400 Bad Request` (Erros de validação):
        ```json
        {
          "cpf": ["O CPF deve conter exatamente 11 dígitos."],
          "nome": ["Este campo não pode ser em branco."]
        }
        ```

#### DELETE `/accounts/auth/me`
**Descrição:** Soft-delete da própria conta do usuário.
*   **Autenticação:** Bearer JWT.
*   **Respostas:**
    *   `204 No Content`: Conta desativada (`ativo=False`).

#### POST `/accounts/auth/google`
**Descrição:** Autentica ou cria conta utilizando o Google OAuth2.
*   **Autenticação:** Nenhuma.
*   **Request Body:**
    | Campo | Tipo | Obrigatório | Descrição |
    |---|---|---|---|
    | `code` | `string` | Sim | Código retornado pelo Google Auth |
    | `redirect_uri` | `string` | Sim | URI de redirect cadastrada |

    ```json
    {
      "code": "4/0AdQt8...",
      "redirect_uri": "http://localhost:3001/login/callback"
    }
    ```
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "access": "google_jwt_access",
          "refresh": "google_jwt_refresh"
        }
        ```
    *   `400 Bad Request` (Código inválido/expirado):
        ```json
        {
          "error": "Código do Google inválido"
        }
        ```

---

### 2. Portal do Cidadão (Morador)

#### GET `/accounts/me/points`
**Descrição:** Retorna o saldo acumulado de pontos obtido por coletas.
*   **Autenticação:** Bearer JWT (apenas perfil `morador`).
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "pontos_acumulados": 185
        }
        ```
    *   `403 Forbidden` (Perfil incorreto):
        ```json
        {
          "detail": "Você não tem permissão para executar esta ação."
        }
        ```

#### GET `/accounts/me/benefits`
**Descrição:** Retorna os descontos de IPTU consolidados por ciclo (ano) do morador.
*   **Autenticação:** Bearer JWT (apenas perfil `morador`).
*   **Respostas:**
    *   `200 OK`:
        ```json
        [
          {
            "id": 1,
            "imovel": 2,
            "programa": 1,
            "ciclo": "06-2025",
            "desconto_percentual": 5.0,
            "atualizado": "2025-06-27T00:15:00Z"
          }
        ]
        ```

#### GET `/accounts/me/program`
**Descrição:** Busca o programa de incentivo de reciclagem ativo no momento.
*   **Autenticação:** Bearer JWT.
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "id": 1,
          "nome": "Programa de Incentivo à Reciclagem 2025",
          "descricao": "Ganhe desconto no seu IPTU reciclando",
          "data_inicio": "2025-01-01",
          "data_fim": "2025-12-31",
          "ativo": true,
          "desconto_maximo": 40.0,
          "regras": {
            "pontos_por_real": 200.0,
            "minimo_para_beneficio": 100,
            "permite_acumulo_ciclos": true
          }
        }
        ```
    *   `404 Not Found`:
        ```json
        {
          "detail": "Nenhum programa ativo."
        }
        ```

---

### 3. Imóveis (`/program/properties`)

#### GET `/program/properties`
**Descrição:** Lista unidades imobiliárias participantes. Se autenticado como morador, retorna apenas as dele.
*   **Autenticação:** Bearer JWT.
*   **Query Params:**
    | Parâmetro | Tipo | Obrigatório | Descrição |
    |---|---|---|---|
    | `bairro` | `string` | Não | Filtra pelo nome do bairro |
    | `cidade` | `string` | Não | Filtra por cidade |
    | `ativo` | `boolean` | Não | Filtra imóveis ativos ou inativos |
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "count": 1,
          "next": null,
          "previous": null,
          "results": [
            {
              "id": 2,
              "inscricao": "01.02.003.0045.001",
              "titular": 2,
              "cep": "62010-000",
              "logradouro": "Rua das Flores",
              "numero": "123",
              "complemento": "Apto 101",
              "bairro": "Centro",
              "cidade": "Sobral",
              "estado": "CE",
              "num_moradores": 3,
              "ativo": true,
              "data_adesao": "2025-06-27",
              "moradores": [
                {
                  "id": 2,
                  "email": "morador@coleta.com",
                  "nome": "João Silva",
                  "cpf": "123.***.***-01"
                }
              ]
            }
          ]
        }
        ```

#### POST `/program/properties`
**Descrição:** Cadastra um novo imóvel residencial vinculado ao titular.
*   **Autenticação:** Bearer JWT.
*   **Request Body:**
    | Campo | Tipo | Obrigatório | Descrição |
    |---|---|---|---|
    | `inscricao` | `string` | Sim | Inscrição Imobiliária (Única) |
    | `titular` | `integer` | Sim | ID do Usuário titular (perfil `morador`) |
    | `cep` | `string` | Sim | CEP (formato XXXXX-XXX ou apenas números) |
    | `logradouro` | `string` | Sim | Rua/avenida (mínimo 3 caracteres) |
    | `numero` | `string` | Sim | Número do lote/casa |
    | `complemento` | `string` | Não | Apartamento, bloco, etc. |
    | `bairro` | `string` | Sim | Nome do bairro |
    | `cidade` | `string` | Sim | Nome da cidade |
    | `estado` | `string` | Sim | Sigla do Estado (2 caracteres) |
    | `num_moradores` | `integer` | Sim | Número de moradores residindo |

    ```json
    {
      "inscricao": "01.02.003.0045.001",
      "titular": 2,
      "cep": "62010-000",
      "logradouro": "Rua das Flores",
      "numero": "123",
      "complemento": "Apto 101",
      "bairro": "Centro",
      "cidade": "Sobral",
      "estado": "CE",
      "num_moradores": 3
    }
    ```
*   **Respostas:**
    *   `201 Created`: Imóvel salvo com sucesso e publicado no RabbitMQ.
    *   `400 Bad Request` (Erros de validação):
        ```json
        {
          "inscricao": ["Imóvel com este campo inscrição já existe."],
          "titular": ["O titular do imóvel precisa ter perfil \"morador\"."]
        }
        ```
    *   `403 Forbidden` (Morador tentando criar para outro titular):
        ```json
        {
          "detail": "Você não tem permissão para executar esta ação."
        }
        ```

---

### 4. Histórico de Coletas & Evidências (`/collection/collections`)

#### GET `/collection/collections`
**Descrição:** Lista coletas efetuadas. Se autenticado como morador, retorna apenas as dele.
*   **Autenticação:** Bearer JWT.
*   **Query Params:**
    | Parâmetro | Tipo | Obrigatório | Descrição |
    |---|---|---|---|
    | `page` | `integer` | Não | Página para paginação (default: 1) |
    | `data_inicio` | `string` | Não | Filtra coletas a partir do dia (formato YYYY-MM-DD) |
    | `data_fim` | `string` | Não | Filtra coletas até o dia (formato YYYY-MM-DD) |
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "count": 1,
          "results": [
            {
              "id": 1,
              "id_microservico": "mc-uuid-2025-06-01",
              "imovel": 2,
              "pontuacao": 25.0,
              "data_hora_coleta": "2025-06-15T10:30:00Z",
              "peso_kg": "12.500"
            }
          ]
        }
        ```

#### GET `/collection/collections/{id}/evidences`
**Descrição:** Retorna a galeria de fotos/evidências vinculadas a uma pesagem.
*   **Autenticação:** Bearer JWT.
*   **Respostas:**
    *   `200 OK`:
        ```json
        [
          {
            "id": 5,
            "coleta": 1,
            "descricao": "Pesagem de papelão e pet",
            "arquivo_url": "http://minio:9000/bucket-coletas/ev.jpg",
            "enviada_em": "2025-06-15T10:32:00Z",
            "enviada_por": 2
          }
        ]
        ```

---

### 5. Contestações (`/collection/disputes`)

#### GET `/collection/disputes`
**Descrição:** Lista as contestações abertas por moradores. Moradores enxergam apenas as próprias.
*   **Autenticação:** Bearer JWT.
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "count": 1,
          "results": [
            {
              "id": 1,
              "coleta": 1,
              "aberta_por": 2,
              "motivo": "Peso divergente do registrado na balança.",
              "status": "em_analise",
              "analisada_por": null,
              "resposta": null,
              "aberta_em": "2025-06-27T01:00:00Z",
              "atualizada_em": "2025-06-27T01:00:00Z"
            }
          ]
        }
        ```

#### POST `/collection/disputes`
**Descrição:** Abre um ticket de contestação sobre uma coleta. Restrito ao perfil `morador`.
*   **Autenticação:** Bearer JWT (Morador).
*   **Request Body:**
    | Campo | Tipo | Obrigatório | Descrição |
    |---|---|---|---|
    | `coleta` | `integer` | Sim | ID da coleta a ser contestada |
    | `motivo` | `string` | Sim | Justificativa do morador (mínimo 10 caracteres) |

    ```json
    {
      "coleta": 1,
      "motivo": "O peso registrado está menor do que o real pesado na balança."
    }
    ```
*   **Respostas:**
    *   `201 Created`: Contestação aberta.
    *   `400 Bad Request` (Divergência de validação):
        ```json
        {
          "motivo": ["O motivo deve ter pelo menos 10 caracteres."],
          "coleta": ["Coleta inexistente ou inválida."]
        }
        ```
    *   `403 Forbidden` (Perfil sem permissão):
        ```json
        {
          "detail": "Apenas moradores podem abrir contestações."
        }
        ```

#### PATCH `/collection/disputes/{id}`
**Descrição:** Analisa e responde a uma contestação. Restrito ao perfil `gestor`.
*   **Autenticação:** Bearer JWT (Gestor).
*   **Request Body:**
    | Campo | Tipo | Obrigatório | Descrição |
    |---|---|---|---|
    | `status` | `string` | Sim | Novo status: `em_analise` \| `aceita` \| `negada` |
    | `resposta` | `string` | Sim | Texto de resposta/parecer do gestor |

    ```json
    {
      "status": "aceita",
      "resposta": "Revisamos a balança e corrigimos o peso registrado."
    }
    ```
*   **Respostas:**
    *   `200 OK`: Contestação atualizada.
    *   `400 Bad Request` (Status inválido):
        ```json
        {
          "status": ["Status inválido. Use: em_analise, aceita ou negada."]
        }
        ```

---
---

## ─── SERVIÇO DE AUDITORIA (Porta 8001 - `/api/audit/`) ───

Acesso restrito ao perfil `gestor`. Registra todas as ações administrativas no banco de dados.

---

### 1. Logs de Auditoria

#### GET `/audit/logs`
**Descrição:** Retorna a listagem paginada dos logs de auditoria das tabelas do Core.
*   **Autenticação:** Bearer JWT (Gestor).
*   **Query Params:**
    | Parâmetro | Tipo | Obrigatório | Descrição |
    |---|---|---|---|
    | `usuario_id` | `integer` | Não | Filtra logs gerados por um usuário específico |
    | `tabela` | `string` | Não | Nome da tabela (ex: "imovel", "programa") |
    | `operacao` | `string` | Não | Operação: `INSERT` \| `UPDATE` \| `DELETE` \| `SELECT` |
    | `data_inicio` | `string` | Não | Filtra a partir de data/hora (formato YYYY-MM-DD) |
    | `data_fim` | `string` | Não | Filtra até data/hora (formato YYYY-MM-DD) |
*   **Respostas:**
    *   `200 OK`:
        ```json
        {
          "count": 482,
          "next": "http://localhost:8001/api/audit/logs?page=2",
          "previous": null,
          "results": [
            {
              "id": 124,
              "timestamp": "2025-06-27T10:15:30Z",
              "usuario_id": 1,
              "usuario_email": "gestor@coleta.com",
              "operacao": "UPDATE",
              "tabela": "imovel",
              "objeto_id": "2",
              "dados_antes": {
                "ativo": false
              },
              "dados_depois": {
                "ativo": true
              },
              "ip_origem": "127.0.0.1",
              "endpoint": "/api/program/properties/2"
            }
          ]
        }
        ```

#### GET `/audit/logs/export`
**Descrição:** Exporta os logs de auditoria filtrados no formato CSV para download.
*   **Autenticação:** Bearer JWT (Gestor).
*   **Query Params:** Mesmos filtros de `/audit/logs` mais `formato=csv`.
*   **Respostas:**
    *   `200 OK`: Arquivo binário de texto CSV contendo os dados tabulados.

---
---

## ─── SERVIÇO DE RELATÓRIOS LLM (Porta 8001 - `/api/reports/`) ───

Acesso restrito ao perfil `gestor`. Integra-se ao LLM (DeepSeek / LM Studio) para relatórios narrativos.

---

### 1. Geração de Relatórios

#### POST `/reports/generate`
**Descrição:** Solicita a geração automática de um relatório qualitativo inteligente.
*   **Autenticação:** Bearer JWT (Gestor).
*   **Request Body:**
    | Campo | Tipo | Obrigatório | Descrição |
    |---|---|---|---|
    | `tipo` | `string` | Sim | Tipo: `participacao` \| `impacto` \| `ranking` \| `auditoria` |
    | `periodo` | `object` | Sim | Objeto contendo `inicio` e `fim` (YYYY-MM-DD) |
    | `programa_id` | `integer` | Sim | ID do programa a consolidar |

    ```json
    {
      "tipo": "impacto",
      "periodo": {
        "inicio": "2025-01-01",
        "fim": "2025-12-31"
      },
      "programa_id": 1
    }
    ```
*   **Respostas:**
    *   `201 Created`:
        ```json
        {
          "id": 8,
          "tipo": "impacto",
          "periodo": {
            "inicio": "2025-01-01",
            "fim": "2025-12-31"
          },
          "programa": 1,
          "relatorio": "### Relatório Narrativo de Impacto\nO programa obteve 2.400% acumulados...",
          "tokens_utilizados": 1145,
          "gerado_em": "2025-06-27T18:00:00Z",
          "gerado_por": 1
        }
        ```
    *   `400 Bad Request` (Dados ou LLM indisponível):
        ```json
        {
          "error": "Falha na comunicação com o provedor de inteligência artificial."
        }
        ```

---
---

## ─── MICROSERVIÇO DE COLETA (Porta 8002) ───

Base URL: `http://localhost:8002/api`  
Autenticação: Bearer JWT (`Authorization: Bearer <token_coletor>`) própria do coletor de campo.

---

### 1. Autenticação do Coletor

#### POST `/auth/register`
**Descrição:** Registra um novo coletor (agente de campo) na base MongoDB.
*   **Autenticação:** Nenhuma.
*   **Request Body:**
    | Campo | Tipo | Obrigatório | Descrição |
    |---|---|---|---|
    | `matricula` | `string` | Sim | Matrícula de identificação única do coletor |
    | `senha` | `string` | Sim | Senha (mínimo 8 caracteres, validada por password policy) |
    | `nome` | `string` | Sim | Nome completo do coletor |
    | `email` | `string` | Sim | E-mail corporativo único |
    | `zona` | `string` | Sim | Região de atuação (ex: "Zona Sul") |
    | `cargo` | `string` | Não | Cargo operacional (default: "Agente de coleta") |

    ```json
    {
      "matricula": "C-12345",
      "senha": "SenhaForte@123",
      "nome": "Carlos Agente",
      "email": "carlos@coleta.com",
      "zona": "Norte"
    }
    ```
*   **Respostas:**
    *   `201 Created`:
        ```json
        {
          "token": "eyJhbGciOi...",
          "user": {
            "id": "60c72b2f9b1d8a0015...",
            "nome": "Carlos Agente",
            "matricula": "C-12345",
            "email": "carlos@coleta.com",
            "avatar_url": null,
            "zona": "Norte",
            "role": "coletor"
          }
        }
        ```
    *   `400 Bad Request` (Dados ausentes ou duplicados):
        ```json
        {
          "error": "Matrícula já cadastrada",
          "field": "matricula"
        }
        ```
        ou
        ```json
        {
          "error": "E-mail já cadastrado",
          "field": "email"
        }
        ```

---

### 2. Operações de Coleta e Sincronização

#### POST `/coletas`
**Descrição:** Registra uma pesagem realizada em campo no imóvel.
*   **Autenticação:** Bearer JWT (Coletor).
*   **Request (Multipart Form Data):**
    | Campo | Tipo | Obrigatório | Descrição |
    |---|---|---|---|
    | `imovel_id` | `string` | Sim | ID do imóvel no MongoDB |
    | `peso_total_kg` | `decimal` | Sim | Peso coletado |
    | `data_hora` | `datetime` | Sim | ISO 8601 data/hora da pesagem |
    | `foto` | `File` | Não | Arquivo binário da foto |
    | `observacoes` | `string` | Não | Observações adicionais |
    | `offline_id` | `string` | Não | UUID temporário gerado no app |

*   **Respostas:**
    *   `201 Created`:
        ```json
        {
          "id": "60c72b2f9b1d...",
          "codigo": "ABCD-1234",
          "imovel_id": "60c72b2f...",
          "coletor_id": "60c72b2f...",
          "status": "confirmada",
          "data_hora": "2025-06-27T10:00:00Z",
          "peso_total_kg": "2.500",
          "foto_url": "http://minio:9000/bucket/coleta.jpg",
          "offline_id": "uuid-temp-1",
          "sincronizado": true
        }
        ```
    *   `400 Bad Request` (Imóvel inexistente ou inativo):
        ```json
        {
          "error": "Imóvel não encontrado",
          "field": "imovel_id"
        }
        ```
    *   `502 Bad Gateway` (Falha no upload para o MinIO):
        ```json
        {
          "error": "Falha ao enviar foto: Connection refused"
        }
        ```

#### POST `/sincronizar`
**Descrição:** Lote (batch) de sincronização de coletas em modo offline.
*   **Autenticação:** Bearer JWT (Coletor).
*   **Request Body:**
    ```json
    {
      "coletas": [
        {
          "imovel_id": "60c72b2f9b...",
          "peso_total_kg": "14.200",
          "data_hora": "2025-06-27T10:00:00Z",
          "offline_id": "uuid-temp-1"
        }
      ]
    }
    ```
*   **Respostas:**
    *   `200 OK`: Se todas as coletas forem sincronizadas com sucesso.
    *   `207 Multi-Status` (Sincronização parcial com erros no lote):
        ```json
        {
          "sincronizadas": 0,
          "erros": 1,
          "resultados": [
            {
              "offline_id": "uuid-temp-1",
              "sucesso": false,
              "coleta_id": null,
              "erro": "Imóvel não elegível para participar"
            }
          ]
        }
        ```

---
---

## ─── CONTRATO DE FILAS RABBITMQ ───

### Fila `imoveis` — Core → MS de Coleta
Disparado a cada alteração em `Imovel` no Core API.
```json
{
  "inscricao_imobiliaria": "01.02.003.0045.001",
  "nome": "João Silva",
  "cpf": "12345678901",
  "endereco": "Rua das Flores",
  "numero": "123",
  "complemento": "Apto 101",
  "bairro": "Centro",
  "latitude": -3.689441,
  "longitude": -40.347895,
  "ativo": true,
  "acao": "adesao_programa"
}
```

### Fila `coletas` — MS de Coleta → Core
Disparado a cada coleta gerada no microserviço para pontuação no Core.
```json
{
  "coleta_id": "60c72b2f9b1d8a00155255ee",
  "inscricao_imobiliaria": "01.02.003.0045.001",
  "peso_total_kg": "12.500",
  "data_hora": "2025-06-15T10:30:00+00:00"
}
```
